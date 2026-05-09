from dataclasses import dataclass, field
from typing import Optional
import yaml
import json
import httpx
import re


@dataclass
class EndpointSpec:
    method: str
    path: str
    name: str
    description: str
    parameters: list
    request_body: Optional[dict] = None
    operation_id: Optional[str] = None


def _load_spec(spec: str) -> dict:
    """Load spec from file path or URL."""
    if spec.startswith("http://") or spec.startswith("https://"):
        response = httpx.get(spec, follow_redirects=True)
        response.raise_for_status()
        text = response.text
    else:
        with open(spec) as f:
            text = f.read()

    if spec.endswith(".json") or (spec.startswith("http") and "json" in spec.lower()):
        return json.loads(text)
    return yaml.safe_load(text)


def _resolve_ref(raw: dict, ref: str) -> dict:
    """Resolve a $ref pointer like '#/components/schemas/Foo' within the spec."""
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    current = raw
    for part in parts:
        current = current.get(part, {})
    return current if isinstance(current, dict) else {}


def _resolve_schema(raw: dict, schema: dict) -> dict:
    """Resolve $ref in a schema, returning the dereferenced schema."""
    if "$ref" in schema:
        resolved = _resolve_ref(raw, schema["$ref"])
        if resolved:
            return _resolve_schema(raw, resolved)
    result = dict(schema)
    if "properties" in result:
        for prop_name, prop_schema in result["properties"].items():
            if isinstance(prop_schema, dict) and "$ref" in prop_schema:
                result["properties"][prop_name] = _resolve_schema(raw, prop_schema)
    if "items" in result and isinstance(result["items"], dict) and "$ref" in result["items"]:
        result["items"] = _resolve_schema(raw, result["items"])
    return result


def _operation_to_name(method: str, path: str, operation_id: Optional[str]) -> str:
    """Convert operation to snake_case tool name."""
    if operation_id:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", operation_id).lower()
        return re.sub(r"[^a-z0-9_]", "_", name)
    path_part = re.sub(r"[{}]", "", path).replace("/", "_").strip("_")
    name = f"{method}_{path_part}".lower()
    return re.sub(r"[^a-z0-9_]", "_", name)


def _deduplicate_names(endpoints: list[EndpointSpec]) -> list[EndpointSpec]:
    """Ensure unique function names by appending _2, _3, etc."""
    seen = {}
    for ep in endpoints:
        name = ep.name
        if name in seen:
            seen[name] += 1
            ep.name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
    return endpoints


def _parse_request_body(raw: dict, body_spec: dict) -> Optional[dict]:
    """Parse requestBody (OpenAPI 3.x) into structured form, resolving $refs."""
    if not body_spec:
        return None
    content = body_spec.get("content", {})
    if not content:
        return None

    first_mime = next(iter(content.keys()))
    media_spec = content[first_mime]
    schema = media_spec.get("schema", {})
    schema = _resolve_schema(raw, schema) if schema else {}

    properties = schema.get("properties", {})
    if not properties:
        return None

    return {
        "required": body_spec.get("required", False),
        "properties": properties,
        "required_fields": schema.get("required", []),
        "content_type": first_mime,
    }


def _parse_swagger2_body(raw: dict, params: list[dict]) -> Optional[dict]:
    """Extract request body from Swagger 2.0 'in: body' parameters."""
    for param in params:
        if param.get("in") == "body":
            schema = param.get("schema", {})
            schema = _resolve_schema(raw, schema) if schema else {}
            properties = schema.get("properties", {})
            if properties:
                return {
                    "required": param.get("required", False),
                    "properties": properties,
                    "required_fields": schema.get("required", []),
                    "content_type": "application/json",
                }
    return None


def _extract_base_url(raw: dict) -> str:
    """Extract base URL from OpenAPI 3.x servers or Swagger 2.0 host/basePath/schemes."""
    servers = raw.get("servers", [])
    if servers:
        return servers[0].get("url", "")

    host = raw.get("host", "")
    base_path = raw.get("basePath", "")
    schemes = raw.get("schemes", ["https"])
    if host:
        scheme = schemes[0] if isinstance(schemes, list) and schemes else "https"
        return f"{scheme}://{host}{base_path}"

    return ""


def _param_type_hint(param: dict) -> str:
    """Return the Python type hint string for a parameter schema."""
    schema = param.get("schema") or param.get("items") or {}
    stype = schema.get("type", "string")
    fmt = schema.get("format", "")

    if stype == "integer" or stype == "number":
        if fmt in ("float", "double"):
            return "float"
        return "int"
    if stype == "boolean":
        return "bool"
    if stype == "array":
        items = schema.get("items", {})
        item_type = items.get("type", "string")
        if item_type == "integer":
            return "list[int]"
        return "list"
    if stype == "object":
        return "dict"
    return "str"


def parse_spec(spec: str, include: Optional[list[str]] = None) -> list[EndpointSpec]:
    """
    Parse an OpenAPI spec and return a list of EndpointSpec objects.

    Handles OpenAPI 3.x and Swagger 2.0. Resolves $ref chains.
    """
    raw = _load_spec(spec)
    paths = raw.get("paths", {})
    endpoints = []

    include_set = None
    if include:
        include_set = set()
        for inc in include:
            parts = inc.strip().split(" ", 1)
            if len(parts) == 2:
                include_set.add(f"{parts[0].upper()} {parts[1]}")

    for path, path_item in paths.items():
        path_params = path_item.get("parameters", []) if isinstance(path_item, dict) else []

        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            if not isinstance(path_item, dict):
                continue
            operation = path_item.get(method)
            if not operation:
                continue

            key = f"{method.upper()} {path}"
            if include_set and key not in include_set:
                continue

            operation_id = operation.get("operationId")
            name = _operation_to_name(method, path, operation_id)
            description = (
                operation.get("description")
                or operation.get("summary")
                or f"{method.upper()} {path}"
            )

            # Merge path-level params with operation-level params
            op_params = list(operation.get("parameters", []))
            path_param_names = {p.get("name") for p in op_params}
            for pp in path_params:
                if pp.get("name") not in path_param_names:
                    op_params.append(pp)

            for p in op_params:
                p["_type"] = _param_type_hint(p)

            # Try OpenAPI 3.x requestBody first, then Swagger 2.0 in:body
            request_body = _parse_request_body(raw, operation.get("requestBody"))
            if request_body is None:
                request_body = _parse_swagger2_body(raw, op_params)

            if request_body:
                for name, prop in request_body.get("properties", {}).items():
                    prop["_type"] = _param_type_hint({"schema": prop})

            endpoints.append(EndpointSpec(
                method=method,
                path=path,
                name=name,
                description=description,
                parameters=op_params,
                request_body=request_body,
                operation_id=operation_id,
            ))

    return _deduplicate_names(endpoints)

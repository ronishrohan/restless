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
        response = httpx.get(spec)
        response.raise_for_status()
        text = response.text
    else:
        with open(spec) as f:
            text = f.read()

    if spec.endswith(".json") or (spec.startswith("http") and "json" in spec):
        return json.loads(text)
    return yaml.safe_load(text)


def _operation_to_name(method: str, path: str, operation_id: Optional[str]) -> str:
    """Convert operation to snake_case tool name."""
    if operation_id:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", operation_id).lower()
        return re.sub(r"[^a-z0-9_]", "_", name)
    path_part = re.sub(r"[{}]", "", path).replace("/", "_").strip("_")
    return f"{method}_{path_part}".lower()


def _parse_request_body(body_spec: dict) -> Optional[dict]:
    if not body_spec:
        return None
    content = body_spec.get("content", {})
    schema = None
    for mime, val in content.items():
        if "json" in mime:
            schema = val.get("schema", {})
            break
    if not schema:
        return None
    return {
        "required": body_spec.get("required", False),
        "properties": schema.get("properties", {}),
        "required_fields": schema.get("required", []),
    }


def parse_spec(spec: str, include: Optional[list[str]] = None) -> list[EndpointSpec]:
    """
    Parse an OpenAPI spec and return a list of EndpointSpec objects.

    include: list of "METHOD /path" strings to filter, e.g. ["GET /pets", "POST /issues"]
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
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if not operation:
                continue

            key = f"{method.upper()} {path}"
            if include_set and key not in include_set:
                continue

            operation_id = operation.get("operationId")
            name = _operation_to_name(method, path, operation_id)
            description = operation.get("description") or operation.get("summary") or f"{method.upper()} {path}"
            parameters = operation.get("parameters", [])
            request_body = _parse_request_body(operation.get("requestBody"))

            endpoints.append(EndpointSpec(
                method=method,
                path=path,
                name=name,
                description=description,
                parameters=parameters,
                request_body=request_body,
                operation_id=operation_id,
            ))

    return endpoints

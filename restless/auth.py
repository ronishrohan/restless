from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuthConfig:
    type: str = "none"
    env_var: str = ""
    header_name: str = ""
    query_param: str = ""


def _resolve_ref(raw: dict, ref: str) -> dict:
    """Resolve a $ref pointer like '#/components/securitySchemes/bearerAuth'."""
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    current = raw
    for part in parts:
        current = current.get(part, {})
    return current if isinstance(current, dict) else {}


def detect_auth(spec: dict, override_type: Optional[str] = None) -> AuthConfig:
    """
    Detect auth scheme from OpenAPI spec securitySchemes.
    override_type takes precedence if provided.
    """
    if override_type:
        return _build_from_override(override_type)

    schemes = spec.get("components", {}).get("securitySchemes", {})
    if not schemes:
        return AuthConfig(type="none")

    for name, scheme in schemes.items():
        if isinstance(scheme, dict) and "$ref" in scheme:
            scheme = _resolve_ref(spec, scheme["$ref"])
            if not scheme:
                continue

        scheme_type = scheme.get("type", "")

        if scheme_type == "http":
            http_scheme = scheme.get("scheme", "").lower()
            if http_scheme == "bearer":
                return AuthConfig(type="bearer", env_var="API_BEARER_TOKEN")
            elif http_scheme == "basic":
                return AuthConfig(type="basic", env_var="API_BASIC_TOKEN")

        elif scheme_type == "apiKey":
            location = scheme.get("in", "header")
            param_name = scheme.get("name", "api_key")
            if location == "header":
                return AuthConfig(
                    type="apikey-header",
                    env_var="API_KEY",
                    header_name=param_name,
                )
            elif location == "query":
                return AuthConfig(
                    type="apikey-query",
                    env_var="API_KEY",
                    query_param=param_name,
                )

        elif scheme_type == "oauth2":
            return AuthConfig(type="bearer", env_var="API_BEARER_TOKEN")

    return AuthConfig(type="none")


def _build_from_override(auth_type: str) -> AuthConfig:
    mapping = {
        "bearer": AuthConfig(type="bearer", env_var="API_BEARER_TOKEN"),
        "apikey-header": AuthConfig(type="apikey-header", env_var="API_KEY", header_name="X-API-Key"),
        "apikey-query": AuthConfig(type="apikey-query", env_var="API_KEY", query_param="api_key"),
        "basic": AuthConfig(type="basic", env_var="API_BASIC_TOKEN"),
    }
    return mapping.get(auth_type, AuthConfig(type="none"))

from restless.auth import detect_auth, AuthConfig


def test_detect_bearer_from_spec():
    spec = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "security": [{"bearerAuth": []}]
    }
    auth = detect_auth(spec)
    assert auth.type == "bearer"
    assert auth.env_var == "API_BEARER_TOKEN"


def test_detect_apikey_header():
    spec = {
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        }
    }
    auth = detect_auth(spec)
    assert auth.type == "apikey-header"
    assert auth.header_name == "X-API-Key"
    assert auth.env_var == "API_KEY"


def test_detect_apikey_query():
    spec = {
        "components": {
            "securitySchemes": {
                "queryKey": {"type": "apiKey", "in": "query", "name": "api_key"}
            }
        }
    }
    auth = detect_auth(spec)
    assert auth.type == "apikey-query"
    assert auth.query_param == "api_key"


def test_no_auth():
    auth = detect_auth({})
    assert auth.type == "none"

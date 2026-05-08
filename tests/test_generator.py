from restless.parser import parse_spec
from restless.auth import detect_auth, AuthConfig
from restless.generator import generate_server


def test_generate_produces_python_file(tmp_path):
    endpoints = parse_spec("tests/fixtures/petstore.yaml")
    auth = AuthConfig(type="none")
    output = tmp_path / "server.py"
    generate_server(endpoints, auth, base_url="https://petstore.example.com", output=str(output))
    assert output.exists()
    content = output.read_text()
    assert "from fastmcp import FastMCP" in content
    assert "def list_pets" in content or "def listpets" in content.lower()


def test_generate_includes_bearer_auth(tmp_path):
    endpoints = parse_spec("tests/fixtures/petstore.yaml")
    auth = AuthConfig(type="bearer", env_var="API_BEARER_TOKEN")
    output = tmp_path / "server.py"
    generate_server(endpoints, auth, base_url="https://api.example.com", output=str(output))
    content = output.read_text()
    assert "API_BEARER_TOKEN" in content
    assert "Bearer" in content


def test_generate_path_param_in_function(tmp_path):
    endpoints = parse_spec("tests/fixtures/petstore.yaml")
    auth = AuthConfig(type="none")
    output = tmp_path / "server.py"
    generate_server(endpoints, auth, base_url="https://api.example.com", output=str(output))
    content = output.read_text()
    assert "petId" in content

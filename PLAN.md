# rest2mcp Implementation Plan

**Goal:** A CLI tool that takes any OpenAPI spec and generates a production-ready MCP server with proper auth, selective endpoint exposure, and LLM-optimized tool descriptions.

**Architecture:** Parse OpenAPI 3.x spec → extract endpoints + auth schemes → render a `server.py` via jinja2 template using the `fastmcp` SDK → optional deepseek pass to improve tool descriptions.

**Tech Stack:** Python, typer (CLI), pyyaml + json (parsing), jinja2 (codegen), fastmcp (generated server), httpx (http calls in generated server), deepseek API (optional description enhancement)

**Differentiators over existing tools:**
- Selective endpoint exposure (`--include "POST /issues,GET /users/{id}"`)
- Proper auth handling (bearer, api key header/query, basic — pulled from env vars)
- LLM pass on tool descriptions so the agent actually understands what each tool does
- Single clean generated `server.py` you can read and edit

---

## File Structure

```
rest2mcp/
├── pyproject.toml
├── README.md
├── rest2mcp/
│   ├── __init__.py
│   ├── cli.py           # typer app — generate + serve commands
│   ├── parser.py        # parse openapi spec → internal EndpointSpec objects
│   ├── generator.py     # render server.py from EndpointSpec list
│   ├── auth.py          # auth scheme detection + env var mapping
│   ├── enhancer.py      # optional LLM pass on descriptions
│   └── templates/
│       └── server.py.j2 # jinja2 template for generated MCP server
└── tests/
    ├── fixtures/
    │   └── petstore.yaml    # sample openapi spec for tests
    ├── test_parser.py
    ├── test_generator.py
    └── test_auth.py
```

---

## Task 1: Project Scaffold

**Objective:** Bare-minimum project that installs and runs `rest2mcp --help`

**Files:**
- Create: `pyproject.toml`
- Create: `rest2mcp/__init__.py`
- Create: `rest2mcp/cli.py`

**Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rest2mcp"
version = "0.1.0"
description = "Generate MCP servers from OpenAPI specs"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "pyyaml>=6.0",
    "jinja2>=3.1",
    "fastmcp>=2.0",
    "httpx>=0.27",
    "rich>=13.0",
]

[project.optional-dependencies]
enhance = ["openai>=1.0"]  # for deepseek-compatible LLM pass

[project.scripts]
rest2mcp = "rest2mcp.cli:app"

[tool.hatch.envs.default]
dependencies = ["pytest", "pytest-asyncio"]
```

**Step 2: Create `rest2mcp/__init__.py`**

```python
__version__ = "0.1.0"
```

**Step 3: Create `rest2mcp/cli.py` skeleton**

```python
import typer
from rich.console import Console

app = typer.Typer(help="Generate MCP servers from OpenAPI specs")
console = Console()

@app.command()
def generate(
    spec: str = typer.Argument(..., help="Path or URL to OpenAPI spec (yaml/json)"),
    output: str = typer.Option("server.py", "--output", "-o", help="Output file path"),
    include: str = typer.Option(None, "--include", help='Comma-separated endpoints to include, e.g. "POST /issues,GET /users/{id}"'),
    auth_type: str = typer.Option(None, "--auth-type", help="bearer | apikey-header | apikey-query | basic"),
    enhance: bool = typer.Option(False, "--enhance", help="Use LLM to improve tool descriptions"),
):
    """Generate an MCP server file from an OpenAPI spec."""
    console.print(f"[bold green]rest2mcp[/bold green] — parsing {spec}")
    # TODO: implement

@app.command()
def serve(
    spec: str = typer.Argument(..., help="Path or URL to OpenAPI spec"),
    include: str = typer.Option(None, "--include"),
    auth_type: str = typer.Option(None, "--auth-type"),
    enhance: bool = typer.Option(False, "--enhance"),
):
    """Generate + immediately run the MCP server."""
    # TODO: implement

if __name__ == "__main__":
    app()
```

**Step 4: Install in dev mode and verify**

```bash
cd ~/rest2mcp
pip install -e ".[enhance]"
rest2mcp --help
```

Expected output: typer help menu with `generate` and `serve` commands listed.

**Step 5: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold with typer CLI"
```

---

## Task 2: OpenAPI Parser

**Objective:** Load a yaml/json OpenAPI spec and return a list of structured `EndpointSpec` objects

**Files:**
- Create: `rest2mcp/parser.py`
- Create: `tests/fixtures/petstore.yaml`
- Create: `tests/test_parser.py`

**Step 1: Write failing tests**

```python
# tests/test_parser.py
from rest2mcp.parser import parse_spec, EndpointSpec

def test_parse_returns_list_of_endpoints():
    result = parse_spec("tests/fixtures/petstore.yaml")
    assert isinstance(result, list)
    assert len(result) > 0

def test_endpoint_has_required_fields():
    result = parse_spec("tests/fixtures/petstore.yaml")
    ep = result[0]
    assert isinstance(ep, EndpointSpec)
    assert ep.method in ("get", "post", "put", "patch", "delete")
    assert ep.path.startswith("/")
    assert isinstance(ep.name, str)
    assert isinstance(ep.description, str)

def test_endpoint_params_parsed():
    result = parse_spec("tests/fixtures/petstore.yaml")
    # petstore has GET /pets/{id} with path param
    get_pet = next(e for e in result if e.path == "/pets/{petId}" and e.method == "get")
    param_names = [p["name"] for p in get_pet.parameters]
    assert "petId" in param_names

def test_filter_by_include():
    result = parse_spec("tests/fixtures/petstore.yaml", include=["GET /pets"])
    assert len(result) == 1
    assert result[0].method == "get"
    assert result[0].path == "/pets"
```

**Step 2: Create petstore fixture**

```yaml
# tests/fixtures/petstore.yaml
openapi: "3.0.0"
info:
  title: Petstore
  version: "1.0.0"
paths:
  /pets:
    get:
      operationId: listPets
      summary: List all pets
      description: Returns all pets from the system
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
      responses:
        "200":
          description: A list of pets
    post:
      operationId: createPet
      summary: Create a pet
      description: Creates a new pet in the store
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
                tag:
                  type: string
      responses:
        "201":
          description: Created
  /pets/{petId}:
    get:
      operationId: showPetById
      summary: Info for a specific pet
      description: Returns info for a pet by ID
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Expected response to a valid request
```

**Step 3: Implement `parser.py`**

```python
# rest2mcp/parser.py
from dataclasses import dataclass, field
from typing import Optional
import yaml
import json
import httpx
import re

@dataclass
class EndpointSpec:
    method: str           # "get", "post", etc.
    path: str             # "/pets/{petId}"
    name: str             # snake_case tool name e.g. "show_pet_by_id"
    description: str      # human description for LLM
    parameters: list      # list of {name, in, required, schema, description}
    request_body: Optional[dict] = None  # {required, properties}
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
        # camelCase to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", operation_id).lower()
        return re.sub(r"[^a-z0-9_]", "_", name)
    # fallback: "get_pets_petid"
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
        include_set = {i.strip().upper() for i in include}

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
```

**Step 4: Run tests**

```bash
pytest tests/test_parser.py -v
```

Expected: 4 passed

**Step 5: Commit**

```bash
git add rest2mcp/parser.py tests/
git commit -m "feat: openapi parser with EndpointSpec dataclass"
```

---

## Task 3: Auth Handler

**Objective:** Detect auth scheme from spec and map to env var names for the generated server

**Files:**
- Create: `rest2mcp/auth.py`
- Create: `tests/test_auth.py`

**Step 1: Write failing tests**

```python
# tests/test_auth.py
from rest2mcp.auth import detect_auth, AuthConfig

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
```

**Step 2: Implement `auth.py`**

```python
# rest2mcp/auth.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AuthConfig:
    type: str = "none"       # none | bearer | apikey-header | apikey-query | basic
    env_var: str = ""        # env var name to pull secret from
    header_name: str = ""    # for apikey-header
    query_param: str = ""    # for apikey-query

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

    # take the first scheme
    for name, scheme in schemes.items():
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
```

**Step 3: Run tests**

```bash
pytest tests/test_auth.py -v
```

Expected: 4 passed

**Step 4: Commit**

```bash
git add rest2mcp/auth.py tests/test_auth.py
git commit -m "feat: auth scheme detection from OpenAPI securitySchemes"
```

---

## Task 4: Jinja2 Server Template

**Objective:** Create the jinja2 template that renders a working `server.py` from parsed endpoints + auth config

**Files:**
- Create: `rest2mcp/templates/server.py.j2`

**The template — create this file:**

```jinja2
# Generated by rest2mcp — https://github.com/{{ github_user }}/rest2mcp
# DO NOT EDIT the auth/http sections — edit your OpenAPI spec instead
# Tool descriptions, names, and logic are fair game to customize

import os
import httpx
from fastmcp import FastMCP

BASE_URL = os.environ.get("API_BASE_URL", "{{ base_url }}")
{% if auth.type == "bearer" %}
AUTH_TOKEN = os.environ.get("{{ auth.env_var }}", "")
{% elif auth.type in ("apikey-header", "apikey-query") %}
API_KEY = os.environ.get("{{ auth.env_var }}", "")
{% elif auth.type == "basic" %}
BASIC_TOKEN = os.environ.get("{{ auth.env_var }}", "")
{% endif %}

def _client() -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    {% if auth.type == "bearer" %}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    {% elif auth.type == "apikey-header" %}
    if API_KEY:
        headers["{{ auth.header_name }}"] = API_KEY
    {% elif auth.type == "basic" %}
    if BASIC_TOKEN:
        headers["Authorization"] = f"Basic {BASIC_TOKEN}"
    {% endif %}
    return httpx.Client(base_url=BASE_URL, headers=headers)

mcp = FastMCP("{{ api_title }}")

{% for ep in endpoints %}
@mcp.tool()
def {{ ep.name }}(
    {%- for param in ep.parameters if param.get("in") in ("path", "query") %}
    {{ param.name }}: {{ "str" if param.schema.get("type") == "string" else "int" if param.schema.get("type") == "integer" else "str" }}{% if not param.get("required", False) %} = None{% endif %},
    {%- endfor %}
    {%- if ep.request_body %}
    {%- for field_name, field_schema in ep.request_body.properties.items() %}
    {{ field_name }}: {{ "str" if field_schema.get("type") == "string" else "int" if field_schema.get("type") == "integer" else "bool" if field_schema.get("type") == "boolean" else "str" }}{% if field_name not in ep.request_body.required_fields %} = None{% endif %},
    {%- endfor %}
    {%- endif %}
) -> dict:
    """{{ ep.description }}"""
    path = "{{ ep.path }}"
    {%- for param in ep.parameters if param.get("in") == "path" %}
    path = path.replace("{{ '{' }}{{ param.name }}{{ '}' }}", str({{ param.name }}))
    {%- endfor %}

    {%- set query_params = ep.parameters | selectattr("in", "equalto", "query") | list %}
    params = {}
    {%- for param in query_params %}
    if {{ param.name }} is not None:
        params["{{ param.name }}"] = {{ param.name }}
    {%- endfor %}
    {% if auth.type == "apikey-query" %}
    if API_KEY:
        params["{{ auth.query_param }}"] = API_KEY
    {% endif %}

    with _client() as client:
        {% if ep.method in ("post", "put", "patch") and ep.request_body %}
        body = {
            {%- for field_name in ep.request_body.properties %}
            "{{ field_name }}": {{ field_name }},
            {%- endfor %}
        }
        body = {k: v for k, v in body.items() if v is not None}
        response = client.{{ ep.method }}(path, json=body, params=params)
        {% else %}
        response = client.{{ ep.method }}(path, params=params)
        {% endif %}
        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"status": response.status_code, "text": response.text}

{% endfor %}

if __name__ == "__main__":
    mcp.run()
```

**Commit:**

```bash
git add rest2mcp/templates/
git commit -m "feat: jinja2 template for MCP server codegen"
```

---

## Task 5: Code Generator

**Objective:** Render the template from parsed endpoints + auth config → write `server.py`

**Files:**
- Create: `rest2mcp/generator.py`
- Create: `tests/test_generator.py`

**Step 1: Write failing tests**

```python
# tests/test_generator.py
from rest2mcp.parser import parse_spec
from rest2mcp.auth import detect_auth, AuthConfig
from rest2mcp.generator import generate_server

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
```

**Step 2: Implement `generator.py`**

```python
# rest2mcp/generator.py
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from rest2mcp.parser import EndpointSpec
from rest2mcp.auth import AuthConfig

TEMPLATES_DIR = Path(__file__).parent / "templates"

def generate_server(
    endpoints: list[EndpointSpec],
    auth: AuthConfig,
    base_url: str,
    output: str = "server.py",
    api_title: str = "API",
    github_user: str = "yourusername",
) -> str:
    """Render server.py from endpoints + auth config. Returns the rendered string."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("server.py.j2")

    rendered = template.render(
        endpoints=endpoints,
        auth=auth,
        base_url=base_url,
        api_title=api_title,
        github_user=github_user,
    )

    with open(output, "w") as f:
        f.write(rendered)

    return rendered
```

**Step 3: Run tests**

```bash
pytest tests/test_generator.py -v
```

Expected: 3 passed

**Step 4: Commit**

```bash
git add rest2mcp/generator.py tests/test_generator.py
git commit -m "feat: code generator renders MCP server.py via jinja2"
```

---

## Task 6: Wire Up CLI

**Objective:** Make `rest2mcp generate api.yaml` and `rest2mcp serve api.yaml` actually work end-to-end

**Files:**
- Modify: `rest2mcp/cli.py`

**Replace the cli.py TODO stubs with:**

```python
import typer
import yaml
import subprocess
import sys
import tempfile
import os
from rich.console import Console
from rich.panel import Panel

from rest2mcp.parser import parse_spec
from rest2mcp.auth import detect_auth, AuthConfig
from rest2mcp.generator import generate_server

app = typer.Typer(help="Generate MCP servers from OpenAPI specs")
console = Console()

def _load_raw_spec(spec: str) -> dict:
    import httpx, json
    if spec.startswith("http"):
        r = httpx.get(spec)
        r.raise_for_status()
        text = r.text
    else:
        with open(spec) as f:
            text = f.read()
    try:
        return json.loads(text)
    except Exception:
        return yaml.safe_load(text)

def _parse_include(include: str | None) -> list[str] | None:
    if not include:
        return None
    return [i.strip() for i in include.split(",")]

@app.command()
def generate(
    spec: str = typer.Argument(..., help="Path or URL to OpenAPI spec (yaml/json)"),
    output: str = typer.Option("server.py", "--output", "-o"),
    include: str = typer.Option(None, "--include", help='e.g. "POST /issues,GET /users/{id}"'),
    auth_type: str = typer.Option(None, "--auth-type", help="bearer | apikey-header | apikey-query | basic"),
    enhance: bool = typer.Option(False, "--enhance", help="Use LLM to improve tool descriptions (needs DEEPSEEK_API_KEY)"),
):
    """Generate an MCP server.py from an OpenAPI spec."""
    console.print(f"[bold green]rest2mcp[/bold green] parsing [cyan]{spec}[/cyan]")

    raw = _load_raw_spec(spec)
    base_url = ""
    servers = raw.get("servers", [])
    if servers:
        base_url = servers[0].get("url", "")
    api_title = raw.get("info", {}).get("title", "API")

    include_list = _parse_include(include)
    endpoints = parse_spec(spec, include=include_list)
    auth = detect_auth(raw, override_type=auth_type)

    if enhance:
        try:
            from rest2mcp.enhancer import enhance_descriptions
            endpoints = enhance_descriptions(endpoints)
            console.print("[dim]LLM description enhancement applied[/dim]")
        except ImportError:
            console.print("[yellow]Install with pip install rest2mcp[enhance] for LLM enhancement[/yellow]")

    generate_server(endpoints, auth, base_url=base_url, output=output, api_title=api_title)

    console.print(Panel(
        f"[bold]Generated:[/bold] {output}\n"
        f"[bold]Endpoints:[/bold] {len(endpoints)}\n"
        f"[bold]Auth:[/bold] {auth.type}\n"
        f"[bold]Base URL:[/bold] {base_url or '(set API_BASE_URL env var)'}\n\n"
        f"[dim]Add to claude code:[/dim]\n"
        f'[cyan]hermes config mcp add {api_title.lower().replace(" ", "-")} python {output}[/cyan]',
        title="✅ Done",
    ))

@app.command()
def serve(
    spec: str = typer.Argument(..., help="Path or URL to OpenAPI spec"),
    include: str = typer.Option(None, "--include"),
    auth_type: str = typer.Option(None, "--auth-type"),
    enhance: bool = typer.Option(False, "--enhance"),
):
    """Generate + immediately run the MCP server (stdio transport)."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        tmp_path = f.name

    raw = _load_raw_spec(spec)
    base_url = raw.get("servers", [{}])[0].get("url", "")
    api_title = raw.get("info", {}).get("title", "API")

    include_list = _parse_include(include)
    endpoints = parse_spec(spec, include=include_list)
    auth = detect_auth(raw, override_type=auth_type)

    generate_server(endpoints, auth, base_url=base_url, output=tmp_path, api_title=api_title)
    console.print(f"[bold green]Serving[/bold green] {len(endpoints)} tools from {spec}")

    subprocess.run([sys.executable, tmp_path], check=True)

if __name__ == "__main__":
    app()
```

**Step 4: Manual end-to-end test**

```bash
rest2mcp generate tests/fixtures/petstore.yaml --output /tmp/petstore_server.py
cat /tmp/petstore_server.py
```

Expected: readable `server.py` with `list_pets`, `create_pet`, `show_pet_by_id` functions

**Step 5: Commit**

```bash
git add rest2mcp/cli.py
git commit -m "feat: wire up generate and serve CLI commands end-to-end"
```

---

## Task 7: LLM Description Enhancer (Optional)

**Objective:** Use deepseek to rewrite tool descriptions to be more useful for LLM agents

**Files:**
- Create: `rest2mcp/enhancer.py`

```python
# rest2mcp/enhancer.py
import os
from openai import OpenAI  # deepseek is openai-compatible
from rest2mcp.parser import EndpointSpec

SYSTEM_PROMPT = """You are improving tool descriptions for an MCP server used by AI agents.
Rewrite the description to be clearer about:
- What the tool does (action + object)
- What key parameters mean
- What it returns
Keep it under 2 sentences. Be direct and specific."""

def enhance_descriptions(endpoints: list[EndpointSpec]) -> list[EndpointSpec]:
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

    enhanced = []
    for ep in endpoints:
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Tool: {ep.name}\nEndpoint: {ep.method.upper()} {ep.path}\nCurrent description: {ep.description}"},
                ],
                max_tokens=100,
            )
            new_desc = response.choices[0].message.content.strip()
            enhanced.append(EndpointSpec(
                **{**ep.__dict__, "description": new_desc}
            ))
        except Exception:
            enhanced.append(ep)  # fallback to original on failure

    return enhanced
```

**Commit:**

```bash
git add rest2mcp/enhancer.py
git commit -m "feat: optional deepseek LLM pass to enhance tool descriptions"
```

---

## Task 8: README

**Objective:** A README that makes the tool self-explanatory. Cover install, usage, all CLI flags, and the MCP config snippet.

**Files:**
- Create: `README.md`

```markdown
# rest2mcp

Generate MCP servers from OpenAPI specs. Any REST API with a spec becomes a set of Claude/Cursor tools in seconds.

## Install

\`\`\`bash
pip install rest2mcp
# with LLM description enhancement:
pip install "rest2mcp[enhance]"
\`\`\`

## Usage

\`\`\`bash
# generate server.py from local spec
rest2mcp generate api.yaml

# from URL
rest2mcp generate --url https://api.linear.app/openapi

# only expose specific endpoints
rest2mcp generate api.yaml --include "POST /issues,GET /users/{id}"

# with auth
rest2mcp generate api.yaml --auth-type bearer

# generate + run immediately
rest2mcp serve api.yaml
\`\`\`

## Auth

Set the relevant env var before running the generated server:

| Auth type | Env var |
|-----------|---------|
| bearer | `API_BEARER_TOKEN` |
| apikey-header | `API_KEY` |
| apikey-query | `API_KEY` |
| basic | `API_BASIC_TOKEN` |
| base url | `API_BASE_URL` |

## Add to Claude Code

After generating `server.py`:

\`\`\`bash
hermes config mcp add my-api python server.py
\`\`\`

## What's different from existing tools

- **Selective exposure** — only expose the endpoints you need
- **Auth that actually works** — bearer/apikey/basic auto-detected, pulled from env vars
- **LLM-optimized descriptions** — `--enhance` flag rewrites descriptions for better agent usability
- **Readable output** — generated `server.py` is clean, editable, not a black box
```

**Commit:**

```bash
git add README.md
git commit -m "docs: README with install, usage, auth, MCP config"
```

---

## Final Verification

```bash
# run full test suite
pytest tests/ -v

# end-to-end test with petstore
rest2mcp generate tests/fixtures/petstore.yaml -o /tmp/test_server.py
python -c "import ast; ast.parse(open('/tmp/test_server.py').read()); print('syntax ok')"

# test with a real api spec
rest2mcp generate --url https://petstore3.swagger.io/api/v3/openapi.json -o /tmp/real_server.py
```

Expected: all tests pass, generated files are valid python

---

## Summary

| Task | Files | Est. time |
|------|-------|-----------|
| 1. Scaffold | pyproject.toml, cli.py | 5 min |
| 2. Parser | parser.py, petstore.yaml, test_parser.py | 15 min |
| 3. Auth | auth.py, test_auth.py | 10 min |
| 4. Template | templates/server.py.j2 | 10 min |
| 5. Generator | generator.py, test_generator.py | 10 min |
| 6. Wire CLI | cli.py | 10 min |
| 7. Enhancer | enhancer.py | 5 min |
| 8. README | README.md | 5 min |

**Total: ~70 min of focused implementation**

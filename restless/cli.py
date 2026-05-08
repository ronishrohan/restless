import typer
import yaml
import subprocess
import sys
import tempfile
import os
from rich.console import Console
from rich.panel import Panel

from restless.parser import parse_spec
from restless.auth import detect_auth, AuthConfig
from restless.generator import generate_server

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
    console.print(f"[bold green]restless[/bold green] parsing [cyan]{spec}[/cyan]")

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
            from restless.enhancer import enhance_descriptions
            endpoints = enhance_descriptions(endpoints)
            console.print("[dim]LLM description enhancement applied[/dim]")
        except ImportError:
            console.print("[yellow]Install with pip install restless[enhance] for LLM enhancement[/yellow]")

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

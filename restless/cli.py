import typer
import yaml
import subprocess
import sys
import tempfile
import os
import re
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from restless.parser import parse_spec, _extract_base_url
from restless.auth import detect_auth, AuthConfig
from restless.generator import generate_server

app = typer.Typer(help="Generate MCP servers from OpenAPI specs")
console = Console()

BANNER = r"""
[bold orange1]
▗ ▜
▛▘█▌▛▘▜▘▐ █▌▛▘▛▘
▌ ▙▖▄▌▐▖▐▖▙▖▄▌▄▌
[/bold orange1]
[dim]REST → MCP   [/dim] [bright_black]|[/bright_black] [dim] any OpenAPI spec → working MCP server [/dim]
"""


def _banner():
    console.print(BANNER)


def _load_raw_spec(spec: str) -> dict:
    import httpx, json
    if spec.startswith("http"):
        r = httpx.get(spec, follow_redirects=True)
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
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: ~/.mcp/servers/<name>.py)"),
    include: str = typer.Option(None, "--include", help='e.g. "POST /issues,GET /users/{id}"'),
    auth_type: str = typer.Option(None, "--auth-type", help="bearer | apikey-header | apikey-query | basic"),
    enhance: bool = typer.Option(False, "--enhance", help="Use LLM to improve tool descriptions (needs DEEPSEEK_API_KEY)"),
):
    """Generate an MCP server.py from an OpenAPI spec."""
    _banner()

    with console.status(f"[bold orange1]loading {spec}...[/bold orange1]", spinner="dots"):
        raw = _load_raw_spec(spec)
    base_url = _extract_base_url(raw)
    api_title = raw.get("info", {}).get("title", "API")
    short_name = api_title.lower().replace(" ", "-").replace("--", "-")
    short_name = re.sub(r"-+", "-", short_name).strip("-")

    if output is None:
        mcp_dir = os.path.expanduser("~/.mcp/servers")
        os.makedirs(mcp_dir, exist_ok=True)
        output = os.path.join(mcp_dir, f"{short_name}.py")

    include_list = _parse_include(include)

    with console.status("[bold orange1]parsing spec...[/bold orange1]", spinner="dots"):
        endpoints = parse_spec(spec, include=include_list)
        auth = detect_auth(raw, override_type=auth_type)

    if not endpoints:
        console.print("[yellow]⚠  no endpoints found — check your spec or --include filter[/yellow]")
        raise typer.Exit(1)

    if enhance:
        with console.status("[bold orange1]enhancing descriptions...[/bold orange1]", spinner="dots"):
            try:
                from restless.enhancer import enhance_descriptions
                endpoints = enhance_descriptions(endpoints)
                console.print("[dim]LLM description enhancement applied[/dim]")
            except ImportError:
                console.print("[yellow]Install with pip install restless[enhance] for LLM enhancement[/yellow]")

    with console.status(f"[bold orange1]generating {output}...[/bold orange1]", spinner="dots"):
        generate_server(endpoints, auth, base_url=base_url, output=output, api_title=api_title)

    table = Table(box=None, show_header=False, padding=(0, 0), border_style="bright_black")
    table.add_column(style="bold bright_cyan", width=14)
    table.add_column(style="white")
    table.add_row("spec", spec)
    table.add_row("output", f"[bold green]{output}[/bold green]")
    table.add_row("endpoints", f"[bold]{len(endpoints)}[/bold] tools")
    table.add_row("auth", auth.type)
    table.add_row("base url", base_url or "[dim](set API_BASE_URL env var)[/dim]")
    console.print(table)

    console.print()
    console.print("[bold orange1]Plug this into your agent now, Enjoy![/bold orange1]")
    console.print()
    config_json = (
        '{\n'
        f'  "mcpServers": {{\n'
        f'    "{short_name}": {{\n'
        f'      "command": "python",\n'
        f'      "args": ["{output}"]\n'
        f'    }}\n'
        f'  }}\n'
        '}'
    )
    prompt = "Help me set up this MCP server:\n\n"
    prompt += f"```json\n{config_json}\n```"
    console.print(f'"{prompt}"')
    console.print()


@app.command()
def serve(
    spec: str = typer.Argument(..., help="Path or URL to OpenAPI spec"),
    include: str = typer.Option(None, "--include"),
    auth_type: str = typer.Option(None, "--auth-type"),
    enhance: bool = typer.Option(False, "--enhance"),
):
    """Generate + immediately run the MCP server (stdio transport)."""
    _banner()

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        tmp_path = f.name

    raw = _load_raw_spec(spec)
    base_url = _extract_base_url(raw)
    api_title = raw.get("info", {}).get("title", "API")

    include_list = _parse_include(include)
    endpoints = parse_spec(spec, include=include_list)
    auth = detect_auth(raw, override_type=auth_type)

    if not endpoints:
        console.print("[yellow]⚠  no endpoints found[/yellow]")
        raise typer.Exit(1)

    generate_server(endpoints, auth, base_url=base_url, output=tmp_path, api_title=api_title)
    console.print(f"[bold green]serving[/bold green] {len(endpoints)} tools from [cyan]{spec}[/cyan]")
    console.print(f"[dim]press Ctrl+C to stop[/dim]\n")

    subprocess.run([sys.executable, tmp_path], check=True)


@app.command()
def setup():
    """Install the restless agent skill so agents can use restless themselves."""
    import restless

    src = Path(restless.__file__).parent / "skills" / "restless" / "SKILL.md"
    dst_dir = Path.home() / ".agents" / "skills" / "restless"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "SKILL.md"

    if src.exists():
        shutil.copy2(src, dst)
        console.print(f"[bold green]✓[/bold green] skill installed → [cyan]{dst}[/cyan]")
    else:
        console.print(f"[red]skill file not found in package[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

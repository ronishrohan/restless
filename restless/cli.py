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
    console.print(f"[bold green]restless[/bold green] — parsing {spec}")
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

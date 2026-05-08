import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from restless.parser import EndpointSpec
from restless.auth import AuthConfig

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

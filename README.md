# restless

```json
REST → MCP
```

Turn any REST API with an OpenAPI spec into an MCP server your agent can use — in one command.

## Install

```bash
pip install rest0less

# or via uv
uv tool install rest0less

# then install the agent skill so agents can use restless themselves
restless setup
```

## Usage

```bash
# from a URL — fetches spec, generates server, prints the prompt
restless generate https://petstore3.swagger.io/api/v3/openapi.json

# from a local file
restless generate api.yaml

# only expose specific endpoints
restless generate api.yaml --include "POST /issues,GET /users/{id}"

# with auth
restless generate api.yaml --auth-type bearer

# generate + run immediately (stdio transport)
restless serve api.yaml

# custom output path (default: ~/.mcp/servers/<name>.py)
restless generate api.yaml -o /path/to/server.py
```

Generated servers live in `~/.mcp/servers/` by default. Override with `-o`.

## Auth

Detected automatically from the spec. Override with `--auth-type`.

| Auth type     | Env var            |
|---------------|--------------------|
| bearer        | `API_BEARER_TOKEN` |
| apikey-header | `API_KEY`          |
| apikey-query  | `API_KEY`          |
| basic         | `API_BASIC_TOKEN`  |
| base url      | `API_BASE_URL`     |

## Output

Every `restless generate` prints a prompt you can paste directly into any agent:

```
Plug this into your agent now, Enjoy!

"Help me set up this MCP server:

```json
{
  "mcpServers": {
    "petstore": {
      "command": "python",
      "args": ["/Users/you/.mcp/servers/petstore.py"]
    }
  }
}
```"
```

Works with Claude Desktop, Claude Code, Cursor, Continue, and any MCP-compatible client.

## Flags

| Flag | Description |
|------|-------------|
| `--include` | Comma-separated endpoints, e.g. `"POST /issues,GET /users/{id}"` |
| `--auth-type` | Force auth: `bearer`, `apikey-header`, `apikey-query`, `basic` |
| `--output`, `-o` | Output path (default: `~/.mcp/servers/<name>.py`) |
| `--enhance` | Use LLM to improve tool descriptions (needs `DEEPSEEK_API_KEY`) |
| `setup` | Install the agent skill so agents can use restless themselves |

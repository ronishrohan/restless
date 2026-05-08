# restless

Generate MCP servers from OpenAPI specs. Any REST API with a spec becomes a set of Claude/Cursor tools in seconds.

## Install

```bash
pip install restless
# with LLM description enhancement:
pip install "restless[enhance]"
```

## Usage

```bash
# generate server.py from local spec
restless generate api.yaml

# from URL
restless generate https://api.example.com/openapi.json

# only expose specific endpoints
restless generate api.yaml --include "POST /issues,GET /users/{id}"

# with auth
restless generate api.yaml --auth-type bearer

# generate + run immediately
restless serve api.yaml
```

## Auth

Set the relevant env var before running the generated server:

| Auth type | Env var |
|-----------|---------|
| bearer | `API_BEARER_TOKEN` |
| apikey-header | `API_KEY` |
| apikey-query | `API_KEY` |
| basic | `API_BASIC_TOKEN` |
| base url | `API_BASE_URL` |

## Add to your MCP client

After generating `server.py`, add it to your MCP client config:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

Works with Claude Desktop, Cursor, Continue, and any MCP-compatible client.

## What's different from existing tools

- **Selective exposure** — only expose the endpoints you need
- **Auth that actually works** — bearer/apikey/basic auto-detected, pulled from env vars
- **LLM-optimized descriptions** — `--enhance` flag rewrites descriptions for better agent usability
- **Readable output** — generated `server.py` is clean, editable, not a black box

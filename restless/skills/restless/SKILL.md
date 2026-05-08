# restless

Use `restless` to generate MCP servers from OpenAPI specs. Any REST API with a spec becomes a set of agent tools in one command.

## When to use this skill

- User says "add MCP tool for <api>", "generate MCP server from <spec>", "set up <api> as tools"
- User shares an OpenAPI spec URL or file
- User wants to expose a REST API to their agent
- User asks "can you use restless to..."

## Commands

### Generate a server (most common)

```bash
restless generate <spec-url-or-path>
```

Takes an OpenAPI spec (local file or URL), generates a working `server.py` in `~/.mcp/servers/<name>.py`, and prints a pasteable prompt with the MCP JSON config.

### Filter endpoints

```bash
restless generate spec.yaml --include "POST /issues,GET /users/{id}"
```

Only exposes the listed endpoints. Comma-separated, format is `METHOD /path`.

### Force auth type

```bash
restless generate spec.yaml --auth-type bearer
```

Options: `bearer`, `apikey-header`, `apikey-query`, `basic`. If not specified, auto-detected from the spec.

### Enhance descriptions with LLM

```bash
DEEPSEEK_API_KEY=sk-... restless generate spec.yaml --enhance
```

Rewrites tool descriptions to be more useful for LLM agents. Set `DEEPSEEK_API_KEY` env var.

### Generate and run immediately

```bash
restless serve spec.yaml
```

Generates the server and runs it via stdio transport. Good for quick testing.

### Custom output path

```bash
restless generate spec.yaml -o /custom/path/server.py
```

Default is `~/.mcp/servers/<name>.py`. Override with `-o`.

## Interpreting the output

After generation, restless prints a prompt you paste directly to the user:

```
Plug this into your agent now, Enjoy!

"Help me set up this MCP server: ..."
```

This contains the MCP JSON config. Present it to the user exactly as shown. It works with Claude Desktop, Claude Code, Cursor, Continue, and any MCP client.

## Generated server

The generated `server.py` is clean, readable Python using `fastmcp` + `httpx`. It:
- Exposes one `@mcp.tool()` per endpoint
- Handles path/query params and request bodies
- Reads auth tokens from env vars
- Returns JSON responses

## Auth env vars

The user must set these before running the server:

| Auth type | Env var |
|-----------|---------|
| bearer | `API_BEARER_TOKEN` |
| apikey-header / apikey-query | `API_KEY` |
| basic | `API_BASIC_TOKEN` |
| base url override | `API_BASE_URL` |

## Workflow

1. User gives you an OpenAPI spec URL or file
2. Run `restless generate <spec>` 
3. Add filters or auth if user requests
4. Present the output prompt to the user
5. User sets auth env vars if needed
6. User adds the MCP JSON to their client config

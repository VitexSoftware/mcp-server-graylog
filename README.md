# mcp-server-graylog

stdio MCP server for Graylog. Two modes, selected by `GRAYLOG_MODE`:

- `bridge` (default) forwards to the MCP endpoint built into **Graylog 7.1+** (`/api/mcp`).
- `api` talks to the REST API directly. The tools match the read-only set from the Connectica Graylog MCP (`graylog-main`), which Ing. Radek Vymazal created: system info, streams, relative search, and field names. That archive depends on a private GitLab library, so this package ships its own HTTP client instead of importing it.

Graylog marks its built-in MCP support as experimental. API mode only calls read endpoints and is the one to use when `/api/mcp` is not enabled.

## Install

    apt install mcp-server-graylog
    apt install mcprack-mcp-server-graylog

## Graylog setup

1. Create a dedicated user and an API token (System > Users and Teams > Tokens).
2. Bridge mode also needs *System > Configurations > MCP* enabled.

## Environment

| Variable | Secret | Default | Meaning |
|---|---|---|---|
| `GRAYLOG_MODE` | no | `bridge` | `bridge` or `api` |
| `GRAYLOG_API_TOKEN` | yes | – | API token. `GRAYLOG_TOKEN` is accepted as an alias. The server builds `Basic base64("<token>:token")` itself |
| `GRAYLOG_URL` | no | `http://127.0.0.1:9000` | Graylog base URL. A trailing `/api` is stripped |
| `GRAYLOG_READ_ONLY` | no | `true` | bridge mode: expose only tools with `readOnlyHint=true` |
| `GRAYLOG_TIMEOUT` | no | `30` | seconds per request |
| `GRAYLOG_VERIFY_TLS` | no | `true` | verify the server certificate |
| `GRAYLOG_MAX_CHARS` | no | `100000` | truncate larger tool output |

## Tools

Bridge mode discovers tools from Graylog at runtime and does not rename them. Missing annotation hints are filled from the tool name.

API mode (`GRAYLOG_MODE=api`) always registers these read-only tools:

| Tool | Title | Annotation |
|---|---|---|
| `server_info` | Server Info | read-only |
| `stream_list` | List Streams | read-only |
| `stream_get` | Get Stream | read-only |
| `search_messages` | Search Messages | read-only |
| `field_list` | List Fields | read-only |

`search_messages` uses `/api/search/universal/relative`. The query is required, the window is at most 24 hours, and a call returns at most 100 messages.

## Development

    PYTHONPATH=src python3 -m pytest

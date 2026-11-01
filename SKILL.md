---
name: graylog-mcp
description: Query Graylog logs, streams and system info through mcp-server-graylog. Use when asked about Graylog messages, streams or fields.
---

Prefer `GRAYLOG_MODE=api` unless the user says Graylog's built-in MCP endpoint is enabled. API mode tools are `server_info`, `stream_list`, `stream_get`, `search_messages` and `field_list`, all read-only. Give searches a Lucene query and a short time window (seconds, max 86400). Bridge mode tools come from Graylog and stay hidden unless `GRAYLOG_READ_ONLY=false`; ask before enabling write tools.

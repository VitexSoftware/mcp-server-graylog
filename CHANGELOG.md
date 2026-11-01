# Changelog

## 1.1.0
- Add `GRAYLOG_MODE=api` with read-only REST tools (system, streams, relative search, fields). The tool list follows the Connectica Graylog MCP created by Ing. Radek Vymazal; the private GitLab client is not used.
- Ship `server.json` for the mcprack config form.

## 1.0.0
- Initial release: stdio bridge to Graylog's `/api/mcp`, read-only by default.

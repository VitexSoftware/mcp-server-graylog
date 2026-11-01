"""Read-only Graylog REST tools.

The tool list follows the Connectica Graylog MCP (the downloaded
graylog-main archive), created by Ing. Radek Vymazal. That project depends
on a private GitLab library, so the HTTP client here is local and the entry
point stays mcp-server-graylog.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import urlencode

from fastmcp import FastMCP
from pydantic import Field

from .annotations import READ_ONLY_ANNOTATIONS
from .httputil import redact, request_json

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class ApiConfig:
    url: str
    token: str
    timeout: float = 30.0
    verify_tls: bool = True
    max_chars: int = 100_000

    @classmethod
    def from_env(cls) -> "ApiConfig":
        url = os.environ.get("GRAYLOG_URL", "http://127.0.0.1:9000").rstrip("/")
        if url.endswith("/api"):
            url = url[: -len("/api")]
        token = os.environ.get("GRAYLOG_API_TOKEN") or os.environ.get("GRAYLOG_TOKEN") or ""
        return cls(
            url=url,
            token=token,
            timeout=float(os.environ.get("GRAYLOG_TIMEOUT", "30")),
            verify_tls=_flag("GRAYLOG_VERIFY_TLS", True),
            max_chars=int(os.environ.get("GRAYLOG_MAX_CHARS", "100000")),
        )

    def auth_header(self) -> str:
        if not self.token:
            raise RuntimeError("GRAYLOG_API_TOKEN is not set")
        return "Basic " + base64.b64encode(f"{self.token}:token".encode()).decode()


def _scheme(url: str) -> None:
    if not url.startswith(("https://", "http://")):
        raise RuntimeError("GRAYLOG_URL must start with http:// or https://")


def call_api(config: ApiConfig, path: str, params: dict[str, Any] | None = None) -> str:
    _scheme(config.url)
    query = ("?" + urlencode(params)) if params else ""
    payload = request_json(
        "GET",
        f"{config.url}{path}{query}",
        headers={
            "Authorization": config.auth_header(),
            "Accept": "application/json",
            "X-Requested-By": "mcp-server-graylog",
        },
        timeout=config.timeout,
        max_chars=config.max_chars,
        verify=config.verify_tls,
    )
    text = json.dumps(redact(payload), default=str)
    if len(text) > config.max_chars:
        return text[: config.max_chars] + f"\n[truncated: output exceeded {config.max_chars} characters]"
    return text


def build_server(config: ApiConfig) -> FastMCP:
    mcp = FastMCP("mcp-server-graylog", instructions="Read-only Graylog REST tools.")

    @mcp.tool(name="server_info", title="Server Info", annotations=READ_ONLY_ANNOTATIONS)
    def server_info() -> str:
        """Read Graylog system information. Requires the matching API permission."""
        return call_api(config, "/api/system")

    @mcp.tool(name="stream_list", title="List Streams", annotations=READ_ONLY_ANNOTATIONS)
    def stream_list() -> str:
        """List Graylog streams visible to the token, within the response-size cap."""
        return call_api(config, "/api/streams")

    @mcp.tool(name="stream_get", title="Get Stream", annotations=READ_ONLY_ANNOTATIONS)
    def stream_get(
        stream_id: Annotated[str, Field(description="Alphanumeric Graylog stream id", min_length=1, max_length=64)],
    ) -> str:
        """Read one Graylog stream by id."""
        if not stream_id.isalnum():
            raise ValueError("Stream ID must be alphanumeric")
        return call_api(config, f"/api/streams/{stream_id}")

    @mcp.tool(name="search_messages", title="Search Messages", annotations=READ_ONLY_ANNOTATIONS)
    def search_messages(
        query: Annotated[str, Field(description="Non-empty Lucene query, at most 2000 characters")],
        seconds: Annotated[int, Field(description="Relative window in seconds, from 1 to 86400")] = 300,
        limit: Annotated[int, Field(description="Maximum messages to return, from 1 to 100")] = 25,
        offset: Annotated[int, Field(description="Result offset, from 0 to 10000")] = 0,
        fields: Annotated[str, Field(description="Comma-separated fields, at most 500 characters")] = "timestamp,source,message",
        stream_id: Annotated[str | None, Field(description="Optional alphanumeric stream id")] = None,
    ) -> str:
        """Search the relative Graylog API. At most 24 hours and 100 messages per call."""
        if not query.strip() or len(query) > 2000:
            raise ValueError("Query must contain 1–2000 characters")
        if not 1 <= seconds <= 86400:
            raise ValueError("Seconds must be between 1 and 86400")
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        if not 0 <= offset <= 10000:
            raise ValueError("Offset must be between 0 and 10000")
        if len(fields) > 500:
            raise ValueError("Fields exceed the allowed length")
        params: dict[str, Any] = {
            "query": query,
            "range": seconds,
            "limit": limit,
            "offset": offset,
            "fields": fields,
            "sort": "timestamp:desc",
            "decorate": "false",
        }
        if stream_id is not None:
            if not stream_id.isalnum():
                raise ValueError("Stream ID must be alphanumeric")
            params["filter"] = "streams:" + stream_id
        return call_api(config, "/api/search/universal/relative", params)

    @mcp.tool(name="field_list", title="List Fields", annotations=READ_ONLY_ANNOTATIONS)
    def field_list() -> str:
        """Read indexed field names, within the response-size cap."""
        return call_api(config, "/api/system/fields")

    return mcp


def main() -> None:
    build_server(ApiConfig.from_env()).run(transport="stdio")

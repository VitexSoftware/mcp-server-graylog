import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server_graylog.api import ApiConfig, build_server
from mcp_server_graylog.httputil import redact


def _config() -> ApiConfig:
    return ApiConfig(url="https://graylog.example", token="SECRET", max_chars=1000)


def _server(monkeypatch, seen):
    def fake(method, url, **kwargs):
        seen.append((method, url, kwargs["headers"]["Authorization"]))
        return {"ok": True, "api_token": "leaked"}

    monkeypatch.setattr("mcp_server_graylog.api.request_json", fake)
    return build_server(_config())


async def test_api_tools_have_titles_and_hints():
    async with Client(build_server(_config())) as client:
        tools = await client.list_tools()
    names = {tool.name for tool in tools}
    assert names == {"server_info", "stream_list", "stream_get", "search_messages", "field_list"}
    for tool in tools:
        assert tool.title and tool.title != tool.name
        ann = tool.annotations
        assert None not in (ann.read_only_hint, ann.destructive_hint, ann.idempotent_hint, ann.open_world_hint)
        assert ann.read_only_hint is True
        assert ann.destructive_hint is False


async def test_search_messages_builds_relative_query(monkeypatch):
    seen = []
    server = _server(monkeypatch, seen)
    async with Client(server) as client:
        result = await client.call_tool(
            "search_messages",
            {"query": "source:test", "seconds": 60, "limit": 2, "stream_id": "abc"},
        )
    assert not result.is_error
    method, url, auth = seen[0]
    assert method == "GET"
    assert url.startswith("https://graylog.example/api/search/universal/relative?")
    assert "range=60" in url
    assert "filter=streams%3Aabc" in url
    assert "SECRET" not in auth or auth.startswith("Basic ")
    text = result.content[0].text
    assert "SECRET" not in text
    assert json.loads(text)["api_token"] == "[REDACTED]"


@pytest.mark.parametrize(
    "args",
    [
        {"query": ""},
        {"query": "x", "seconds": 86401},
        {"query": "x", "limit": 101},
        {"query": "x", "offset": -1},
        {"query": "x", "fields": "x" * 501},
        {"query": "x", "stream_id": "a:b"},
    ],
)
async def test_invalid_search_does_not_call_api(monkeypatch, args):
    seen = []
    server = _server(monkeypatch, seen)
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool("search_messages", args)
    assert seen == []


def test_missing_token_message_has_no_header():
    with pytest.raises(RuntimeError, match="GRAYLOG_API_TOKEN") as exc:
        ApiConfig(url="https://graylog.example", token="").auth_header()
    assert "Basic" not in str(exc.value)


def test_redact_nested_token():
    assert redact({"user": "a", "nested": {"password": "x"}})["nested"]["password"] == "[REDACTED]"


def test_readme_lists_server_json_env(tmp_path=None):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text()
    manifest = json.loads((root / "debian" / "server.json").read_text())
    for item in manifest["environmentVariables"]:
        assert item["name"] in readme

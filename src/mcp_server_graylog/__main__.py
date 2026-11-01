import argparse
import os

from . import __version__
from .server import main as run_bridge


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-server-graylog",
        description="stdio MCP server for Graylog. GRAYLOG_MODE=bridge (default) forwards "
        "to Graylog 7.1+ /api/mcp. GRAYLOG_MODE=api exposes read-only REST tools "
        "(server_info, stream_list, stream_get, search_messages, field_list). "
        "Env: GRAYLOG_URL, GRAYLOG_API_TOKEN, GRAYLOG_READ_ONLY, GRAYLOG_TIMEOUT, "
        "GRAYLOG_VERIFY_TLS, GRAYLOG_MAX_CHARS.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args()
    mode = os.environ.get("GRAYLOG_MODE", "bridge").strip().lower()
    if mode == "api":
        from .api import main as run_api

        run_api()
        return
    if mode != "bridge":
        raise SystemExit("GRAYLOG_MODE must be 'bridge' or 'api'")
    run_bridge()


if __name__ == "__main__":
    main()

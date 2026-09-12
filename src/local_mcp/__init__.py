import os
import sys

from watchdog.observers import Observer

from config.config import INBOX_DIR
from local_mcp.server import mcp
from local_rag.watcher.handler import PDFHandler


def main() -> None:
    transport = os.getenv("FASTMCP_TRANSPORT", "sse")
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))

    print("Starting PDF watcher...", file=sys.stderr)
    print(f"[*] Watching {INBOX_DIR} for new PDFs...", file=sys.stderr)
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, INBOX_DIR, recursive=False)
    observer.start()

    try:
        if transport in ("http", "sse", "streamable-http"):
            print(
                f"[*] Starting MCP & REST API server on http://{host}:{port} ({transport})...",
                file=sys.stderr,
            )
            mcp.run(transport=transport, host=host, port=port)
        else:
            print("[*] Starting MCP server over stdio...", file=sys.stderr)
            mcp.run(transport="stdio")
    finally:
        observer.stop()
        observer.join()

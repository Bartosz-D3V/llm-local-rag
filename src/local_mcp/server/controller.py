import asyncio
import os
import signal
import sys
from pathlib import Path

from fastmcp import FastMCP

from local_mcp.config.config import INBOX_DIR
from local_mcp.file.handler import PDFFileHandler
from local_mcp.file.watcher import folder_name_to_table
from local_mcp.rag.repository import VectorStoreRepository


class MCPController:
    def __init__(
        self, pdf_handler: PDFFileHandler, repository: VectorStoreRepository
    ) -> None:
        self.pdf_handler = pdf_handler
        self.repository = repository

    def _make_search_tool(
        self, mcp: FastMCP, table_name: str, description: str
    ) -> None:
        """Dynamically register a per-folder search tool on the MCP server."""

        @mcp.tool(name=f"search_{table_name}", description=description)
        def _search(query: str, top_k: int = 5) -> str:
            return self.repository.search(table_name, query, top_k)

    def register_inbox_tools(self, mcp: FastMCP) -> None:
        """Scan documentation folder, register one MCP tool per folder that has a description.md."""
        inbox = Path(INBOX_DIR)
        print(f"[*] Scanning {inbox} for documentation folders...", file=sys.stderr)
        for folder in sorted(inbox.iterdir()):
            if not folder.is_dir():
                continue

            # Read and validate description.md for the folder
            description_file = folder / "description.md"
            if not description_file.exists():
                print(
                    f"[Startup] Skipping '{folder.name}': missing description.md",
                    file=sys.stderr,
                )
                continue

            description = description_file.read_text().strip()
            if not description:
                print(
                    f"[Startup] Skipping '{folder.name}': description.md is empty",
                    file=sys.stderr,
                )
                continue

            # Process table name based on the folder name
            table_name = folder_name_to_table(folder.name)
            self._make_search_tool(mcp, table_name, description)
            print(
                f"[Startup] Registered tool 'search_{table_name}' for folder '{folder.name}'",
                file=sys.stderr,
            )

    @staticmethod
    def handle_shutdown_signal(sig, frame):
        """Graceful signal trap for SIGTERM sent by CLI managers."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        sys.exit(0)

    def _get_mcp(self):
        # Catch SIGTERM (sent by CLI when stopping instance) and SIGINT (Ctrl+C)
        signal.signal(signal.SIGTERM, MCPController.handle_shutdown_signal)
        signal.signal(signal.SIGINT, MCPController.handle_shutdown_signal)

        # Setup FastMCP server and register per-folder tools
        mcp = FastMCP("Local Private RAG")
        self.register_inbox_tools(mcp)

        return mcp

    def start(self):
        transport = os.getenv("FASTMCP_TRANSPORT", "stdio")
        host = os.getenv("FASTMCP_HOST", "127.0.0.1")
        port = int(os.getenv("FASTMCP_PORT", "8000"))

        mcp = self._get_mcp()
        if transport in ("http", "sse", "streamable-http"):
            print(
                f"[*] Starting MCP & REST API server on http://{host}:{port} ({transport})...",
                file=sys.stderr,
            )
            mcp.run(transport=transport, host=host, port=port)
        else:
            print("[*] Starting MCP server over stdio...", file=sys.stderr)
            mcp.run(transport="stdio", show_banner=False)

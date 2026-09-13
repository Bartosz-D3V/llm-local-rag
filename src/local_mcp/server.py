import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import signal
import sys

import lancedb
from fastmcp import FastMCP

from config.config import DB_DIR, INBOX_DIR
from local_models.vectorizer import get_local_embedding
from local_rag.vectorization.main import process_pdf
from local_rag.watcher.handler import folder_name_to_table


def _make_search_tool(mcp: FastMCP, table_name: str, description: str) -> None:
    """Dynamically register a per-folder search tool on the MCP server."""

    @mcp.tool(name=f"search_{table_name}", description=description)
    def _search(query: str, top_k: int = 5) -> str:
        db = lancedb.connect(DB_DIR)
        if table_name not in db.table_names():
            return f"No documents indexed for '{table_name}' yet."

        table = db.open_table(table_name)
        query_vector = get_local_embedding(query)
        results = table.search(query_vector).limit(top_k).to_list()
        if not results:
            return "No relevant information found."

        formatted = []
        for r in results:
            score = 1 - r.get("_distance", 0)
            formatted.append(
                f"--- Source: {r['source']} (relevance: {score:.2f}) ---\n{r['text']}\n"
            )
        return "\n".join(formatted)


def register_inbox_tools(mcp: FastMCP) -> None:
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

        # Ingest any PDFs in the folder at startup
        for pdf in sorted(folder.glob("*.pdf")):
            process_pdf(str(pdf), table_name)

        _make_search_tool(mcp, table_name, description)
        print(
            f"[Startup] Registered tool 'search_{table_name}' for folder '{folder.name}'",
            file=sys.stderr,
        )


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    print("MCP Server starting...", file=sys.stderr)
    try:
        yield
    finally:
        print("MCP Server shutting down cleanly...", file=sys.stderr)


def handle_shutdown_signal(sig, frame):
    """Graceful signal trap for SIGTERM sent by CLI managers."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.stop()
    sys.exit(0)


# Catch SIGTERM (sent by CLI when stopping instance) and SIGINT (Ctrl+C)
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)

# Setup FastMCP server and register per-folder tools
mcp = FastMCP("Local Private RAG", lifespan=server_lifespan)
register_inbox_tools(mcp)


if __name__ == "__main__":
    mcp.run()

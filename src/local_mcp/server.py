import asyncio
from contextlib import asynccontextmanager
import signal
import sys

import lancedb
from fastmcp import FastMCP

from config.config import DB_DIR
from local_models.vectorizer import get_local_embedding


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    # Startup tasks (if any)
    print("MCP Server starting...")
    try:
        yield
    finally:
        # Cleanup tasks (close DBs, active tasks, etc.)
        print("MCP Server shutting down cleanly...")
        # Add any explicit connection/session cleanups here


def handle_shutdown_signal(sig, frame):
    """Graceful signal trap for SIGTERM sent by CLI managers."""
    # Stop the running event loop cleanly
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.stop()
    sys.exit(0)


# Catch SIGTERM (sent by CLI when stopping instance) and SIGINT (Ctrl+C)
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)

# Setup paths and FastMCP server
mcp = FastMCP("Local Private RAG", lifespan=server_lifespan)


@mcp.tool()
def search_local_documents(query: str, top_k: int = 5) -> str:
    """
    Search local PDF documents for relevant information.
    Returns the most relevant text chunks matching the user query.
    """
    db = lancedb.connect(DB_DIR)

    if "documents" not in db.table_names():
        return "No documents found in the vector database. Drop PDFs into ~/pdf_inbox first."

    table = db.open_table("documents")

    # Generate query embedding locally
    query_vector = get_local_embedding(query)

    # Perform vector similarity search
    results = table.search(query_vector).limit(top_k).to_list()

    if not results:
        return "No relevant information found."

    formatted_output = []
    for r in results:
        for r in results:
            score = 1 - r.get("_distance", 0)  # cosine similarity
            formatted_output.append(
                f"--- Source: {r['source']} (relevance: {score:.2f}) ---\n{r['text']}\n"
            )

    return "\n".join(formatted_output)


if __name__ == "__main__":
    mcp.run()

# Connect to LanceDB local volume
import lancedb

from local_mcp.config.config import DB_DIR

db = lancedb.connect(DB_DIR)

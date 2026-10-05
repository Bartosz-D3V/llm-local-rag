# Connect to LanceDB local volume
from local_mcp.config.config import DB_DIR
import lancedb

db = lancedb.connect(DB_DIR)

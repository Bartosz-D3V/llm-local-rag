# Connect to LanceDB local volume
from config.config import DB_DIR
import lancedb

db = lancedb.connect(DB_DIR)

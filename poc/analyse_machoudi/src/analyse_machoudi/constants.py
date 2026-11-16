import os

# Folder containing this file
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "data")

# Default pattern used to find the raw CSV file
DEFAULT_PATTERN = "*.csv"

# Logging configuration
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = "INFO"

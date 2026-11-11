"""Project-wide logging configuration.

Every module imports the shared ``logging`` object from here so that all output
lands in one timestamped file under ``logs/``. The location can be overridden
with the ``US_VISA_LOG_DIR`` environment variable (handy in containers).
"""

import logging
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOG_DIR = Path(os.getenv("US_VISA_LOG_DIR", PROJECT_ROOT / "logs"))
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_FILE_PATH = LOG_DIR / LOG_FILE

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE_PATH),
    format="[ %(asctime)s ] %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

__all__ = ["LOG_DIR", "LOG_FILE", "LOG_FILE_PATH", "PROJECT_ROOT", "logging"]

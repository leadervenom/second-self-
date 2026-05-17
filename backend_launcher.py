import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from src.server import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
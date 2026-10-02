import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
INDEX_DIR = BASE_DIR / "data" / "index"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_FAST_MODEL = "gemini-1.5-flash"
DEFAULT_ACCURATE_MODEL = "gemini-1.5-pro"

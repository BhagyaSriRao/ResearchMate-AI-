from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def get_env_var(key, default=""):
    load_dotenv(ROOT / ".env", override=True)
    val = os.getenv(key, default)
    if val is None:
        return default
    return str(val).strip().strip("'\"")

load_dotenv(ROOT / ".env", override=True)
DB_PATH = ROOT / os.getenv("DATABASE_PATH", "data/researchmate.db")
VECTOR_PATH = ROOT / os.getenv("VECTOR_PATH", "data/chroma")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
CROSSREF_EMAIL = os.getenv("CROSSREF_EMAIL", "").strip()


import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./contest.db")

# Parse ADMIN_IDS from env: "123456,789012"
_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS is not set or empty in environment variables")

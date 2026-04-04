import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./contest.db")

# Parse ADMIN_IDS from env: "123456,789012"
_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()]

# Redis — optional, falls back to MemoryStorage if not set
REDIS_URL: str = os.getenv("REDIS_URL", "")

# Webhook settings
# Set WEBHOOK_HOST to your Railway public domain, e.g. https://mybot.up.railway.app
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
WEBAPP_PORT: int = int(os.getenv("PORT", "8080"))
WEBAPP_HOST: str = "0.0.0.0"

# If WEBHOOK_HOST is set — use webhook mode, otherwise polling
USE_WEBHOOK: bool = bool(WEBHOOK_HOST)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS is not set or empty in environment variables")

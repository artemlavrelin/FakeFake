import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./contest.db")

_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()]

REDIS_URL: str = os.getenv("REDIS_URL", "")

_raw_group = os.getenv("GROUP_ID", "0")
GROUP_ID: int = int(_raw_group) if _raw_group.lstrip("-").isdigit() else 0

_raw_moder = os.getenv("MODER_GROUP_ID", "-1003654223457")
MODER_GROUP_ID: int = int(_raw_moder) if _raw_moder.lstrip("-").isdigit() else 0

BOT_USERNAME: str = os.getenv("BOT_USERNAME", "taskpaycryptoplaybot")
BOT_LINK: str = f"https://t.me/{BOT_USERNAME}"

REPORT_CHANNEL_URL: str = "https://t.me/mutedcommunication"
REPORT_CHANNEL_TITLE: str = "🔕 MUTED"

STAKE_URL: str    = os.getenv("STAKE_URL",    "https://stake.com/?c=ref")
BINANCE_URL: str  = os.getenv("BINANCE_URL",  "https://accounts.binance.com/register")

FACEBOOK_URL: str  = os.getenv("FACEBOOK_URL",  "https://facebook.com")
TWITTER_URL: str   = os.getenv("TWITTER_URL",   "https://twitter.com")
INSTAGRAM_URL: str = os.getenv("INSTAGRAM_URL", "https://instagram.com")
THREADS_URL: str   = os.getenv("THREADS_URL",   "https://threads.net")

BOT_GREETING: str = os.getenv("BOT_GREETING", "🃏 Bellamy Spake")

WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: str  = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
WEBAPP_PORT: int  = int(os.getenv("PORT", "8080"))
WEBAPP_HOST: str  = "0.0.0.0"
USE_WEBHOOK: bool = bool(WEBHOOK_HOST)

REVIEW_COOLDOWN_HOURS: int        = int(os.getenv("REVIEW_COOLDOWN_HOURS", "12"))
LOOT_COOLDOWN_HOURS: int          = int(os.getenv("LOOT_COOLDOWN_HOURS", "24"))
PAYMENT_CHANGE_COOLDOWN_DAYS: int = int(os.getenv("PAYMENT_CHANGE_COOLDOWN_DAYS", "7"))

# Slot system
SLOT_SPINS_MIN: int = int(os.getenv("SLOT_SPINS_MIN", "69"))
SLOT_SPINS_MAX: int = int(os.getenv("SLOT_SPINS_MAX", "250"))
BUDAPEST_TZ: str    = "Europe/Budapest"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")
if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS is not set or empty")

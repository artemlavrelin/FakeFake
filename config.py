import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./contest.db")

_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()]

REDIS_URL: str = os.getenv("REDIS_URL", "")

# Closed community group (bot must be admin there)
_raw_group = os.getenv("GROUP_ID", "0")
GROUP_ID: int = int(_raw_group) if _raw_group.lstrip("-").isdigit() else 0

# Moderator group — receives bonus draw results
_raw_moder = os.getenv("MODER_GROUP_ID", "-4843909295")
MODER_GROUP_ID: int = int(_raw_moder) if _raw_moder.lstrip("-").isdigit() else -4843909295

# Bot username without @ — used for deep links
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")

# Report channel link
REPORT_CHANNEL_URL: str = "https://t.me/mutedcommunication"
REPORT_CHANNEL_TITLE: str = "🔕 MUTED"

# Webhook
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
WEBAPP_PORT: int = int(os.getenv("PORT", "8080"))
WEBAPP_HOST: str = "0.0.0.0"
USE_WEBHOOK: bool = bool(WEBHOOK_HOST)

# Static ATM intro text (can be overridden in env)
ATM_INTRO: str = os.getenv(
    "ATM_INTRO",
    "Сохраните ваши платёжные данные для получения выигрышей.",
)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")
if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS is not set or empty")

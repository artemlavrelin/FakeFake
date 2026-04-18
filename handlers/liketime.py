"""
/liketime <url> <count> — raffle among users who reacted to a post.
Admin-only. Bot must be admin of the referenced channel.
"""
import random
import re

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, MODER_GROUP_ID
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

# Matches https://t.me/username/123 or https://t.me/c/1234567890/123
_URL_RE = re.compile(
    r"https?://t\.me/"
    r"(?:(?P<username>[a-zA-Z0-9_]{5,})|c/(?P<chat_id>-?\d+))"
    r"/(?P<msg_id>\d+)"
)


def _parse_url(url: str) -> tuple[str | None, int | None]:
    """Return (chat_identifier, message_id) or (None, None) on parse error."""
    m = _URL_RE.match(url.strip())
    if not m:
        return None, None
    msg_id = int(m.group("msg_id"))
    if m.group("username"):
        return f"@{m.group('username')}", msg_id
    return int(m.group("chat_id")), msg_id


async def _get_reactors(bot: Bot, chat_id, message_id: int) -> list[int]:
    """
    Fetch all users who reacted to a message.
    Uses getMessageReactors (Bot API 7.0+).
    Returns list of telegram user IDs.
    """
    user_ids: list[int] = []
    try:
        # Paginate through all reactors (100 per page)
        while True:
            reactors = await bot.get_message_reactors(
                chat_id=chat_id,
                message_id=message_id,
                limit=100,
            )
            if not reactors:
                break
            for r in reactors:
                # r.type == "user" for regular emoji reactions by users
                if hasattr(r, "user") and r.user:
                    user_ids.append(r.user.id)
            if len(reactors) < 100:
                break
    except (TelegramBadRequest, AttributeError) as e:
        logger.warning("get_message_reactors failed | %s", e)
        raise
    return user_ids


async def _is_subscribed(bot: Bot, chat_id, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def _is_channel_admin(bot: Bot, chat_id, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@router.message(Command("liketime"))
async def cmd_liketime(message: Message, bot: Bot) -> None:
    # Check bot-level admin
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "📖 Использование: /liketime <ссылка> <количество_победителей>\n"
            "Пример: /liketime https://t.me/channel_name/123 3"
        )
        return

    url   = parts[1]
    count_str = parts[2]
    if not count_str.isdigit() or int(count_str) < 1:
        await message.answer("⚠️ Количество победителей должно быть числом ≥ 1")
        return

    winners_count = int(count_str)
    chat_id, msg_id = _parse_url(url)

    if chat_id is None:
        await message.answer("❌ Ошибка ссылки")
        return

    # Verify sender is admin of that channel too
    is_admin = await _is_channel_admin(bot, chat_id, message.from_user.id)
    if not is_admin:
        await message.answer("Нет доступа")
        return

    await message.answer("⏳ Получаю список реакций...")

    # Get reactors
    try:
        all_reactor_ids = await _get_reactors(bot, chat_id, msg_id)
    except Exception as e:
        await message.answer(f"❌ Не удалось получить реакции: {e}")
        return

    if not all_reactor_ids:
        await message.answer("❌ Нет участников")
        return

    # Remove duplicates
    all_reactor_ids = list(set(all_reactor_ids))

    await message.answer(f"🔍 Реакций: {len(all_reactor_ids)}. Проверяю подписки...")

    # Filter: only subscribed users
    valid: list[int] = []
    for uid in all_reactor_ids:
        if await _is_subscribed(bot, chat_id, uid):
            valid.append(uid)

    if not valid:
        await message.answer("❌ Нет подписанных участников")
        return

    # Draw
    actual   = min(winners_count, len(valid))
    selected = random.sample(valid, actual)

    logger.info(
        "Liketime draw | chat=%s | msg=%s | total_reactors=%s | valid=%s | winners=%s",
        chat_id, msg_id, len(all_reactor_ids), len(valid), selected,
    )

    # Send winner IDs to moder group
    if MODER_GROUP_ID:
        ids_text = "\n".join(str(uid) for uid in selected)
        try:
            await bot.send_message(
                MODER_GROUP_ID,
                f"🎲 <b>Liketime победители</b>\n"
                f"Пост: {url}\n\n"
                f"{ids_text}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send liketime results to moder group | %s", e)

    # Announce in chat
    await message.answer(
        f"🎊 <b>Розыгрыш завершён</b>\n\n"
        f"👥 Участников: <b>{len(valid)}</b>\n"
        f"🏆 Победителей: <b>{actual}</b>\n\n"
        f"<b>Победители (ID):</b>\n" + "\n".join(f"• <code>{uid}</code>" for uid in selected),
        parse_mode="HTML",
    )

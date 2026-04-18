"""
/liketime <url> <count>

Gets users who reacted to a post using the raw Telegram Bot API
(getMessageReactors — Bot API 7.0+).
Falls back gracefully if the method is unsupported.
"""
import random
import re

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS, MODER_GROUP_ID
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

_URL_RE = re.compile(
    r"https?://t\.me/"
    r"(?:(?P<username>[a-zA-Z0-9_]{5,})|c/(?P<chat_id>-?\d+))"
    r"/(?P<msg_id>\d+)"
)


def _parse_url(url: str):
    """Returns (chat_id_or_username, message_id) or (None, None)."""
    m = _URL_RE.match(url.strip())
    if not m:
        return None, None
    msg_id = int(m.group("msg_id"))
    if m.group("username"):
        return f"@{m.group('username')}", msg_id
    return int(m.group("chat_id")), msg_id


async def _get_reactors_raw(bot: Bot, chat_id, message_id: int) -> list[int]:
    """
    Call getMessageReactors via raw Bot API request.
    Returns list of user IDs who reacted.
    Raises RuntimeError if the method is not available or returns no data.
    """
    user_ids: list[int] = []
    offset = 0
    limit  = 100

    while True:
        try:
            result = await bot.session.api.request(
                token=bot.token,
                method="getMessageReactors",
                data={
                    "chat_id":    str(chat_id),
                    "message_id": message_id,
                    "limit":      limit,
                    "offset":     offset,
                },
            )
        except TelegramBadRequest as e:
            raise RuntimeError(f"getMessageReactors failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"API error: {e}") from e

        # result is the raw JSON — handle both dict and list responses
        reactors = result if isinstance(result, list) else (result or [])

        if not reactors:
            break

        for r in reactors:
            # Each reactor: {"type": "user", "user": {"id": ..., ...}}
            if isinstance(r, dict):
                user_data = r.get("user") or {}
                uid = user_data.get("id")
                if uid:
                    user_ids.append(int(uid))

        if len(reactors) < limit:
            break
        offset += limit

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
    # Must be a global admin
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "📖 Использование: /liketime <ссылка на пост> <количество победителей>\n"
            "Пример: /liketime https://t.me/channel_name/123 3"
        )
        return

    url       = parts[1]
    count_str = parts[2]

    if not count_str.isdigit() or int(count_str) < 1:
        await message.answer("⚠️ Количество победителей — целое число ≥ 1")
        return

    winners_count = int(count_str)
    chat_id, msg_id = _parse_url(url)

    if chat_id is None:
        await message.answer("❌ Ошибка ссылки — проверьте формат: https://t.me/channel/123")
        return

    # Check that caller is admin of that channel
    is_admin = await _is_channel_admin(bot, chat_id, message.from_user.id)
    if not is_admin:
        await message.answer("Нет доступа (вы не администратор этого канала)")
        return

    status_msg = await message.answer("⏳ Получаю список реакций...")

    # Fetch reactors via raw API
    try:
        raw_ids = await _get_reactors_raw(bot, chat_id, msg_id)
    except RuntimeError as e:
        await status_msg.edit_text(
            f"❌ Не удалось получить реакции.\n\n"
            f"Убедитесь что:\n"
            f"• Бот является администратором канала\n"
            f"• Bot API версия ≥ 7.0 поддерживается сервером\n\n"
            f"Детали: <code>{e}</code>",
            parse_mode="HTML",
        )
        logger.error("liketime getMessageReactors error | %s", e)
        return

    if not raw_ids:
        await status_msg.edit_text("❌ Нет участников (никто не поставил реакцию)")
        return

    unique_ids = list(set(raw_ids))
    await status_msg.edit_text(
        f"🔍 Реакций: {len(unique_ids)}. Проверяю подписки..."
    )

    # Filter: only subscribed users
    valid: list[int] = []
    for uid in unique_ids:
        if await _is_subscribed(bot, chat_id, uid):
            valid.append(uid)

    if not valid:
        await status_msg.edit_text("❌ Нет подписанных участников")
        return

    # Draw
    actual   = min(winners_count, len(valid))
    selected = random.sample(valid, actual)

    logger.info(
        "Liketime draw | chat=%s | msg=%s | reactors=%s | valid=%s | winners=%s",
        chat_id, msg_id, len(unique_ids), len(valid), selected,
    )

    # Send only IDs to moder group
    if MODER_GROUP_ID:
        ids_block = "\n".join(str(uid) for uid in selected)
        try:
            await bot.send_message(
                MODER_GROUP_ID,
                f"🎲 <b>Liketime победители</b>\n"
                f"Пост: {url}\n\n"
                f"<b>ID победителей:</b>\n{ids_block}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send liketime to moder group | %s", e)

    # Announce result in chat
    ids_list = "\n".join(f"• <code>{uid}</code>" for uid in selected)
    await status_msg.edit_text(
        f"🎊 <b>Розыгрыш завершён</b>\n\n"
        f"👥 Участников (с подпиской): <b>{len(valid)}</b>\n"
        f"🏆 Победителей: <b>{actual}</b>\n\n"
        f"<b>Победители (ID):</b>\n{ids_list}",
        parse_mode="HTML",
    )

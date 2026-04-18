"""
/liketime <url> <count>

Uses direct aiohttp POST to Telegram Bot API getMessageReactors endpoint
(Bot API 7.0+) — bypasses aiogram session wrapper entirely.
"""
import random
import re

import aiohttp
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS, BOT_TOKEN, MODER_GROUP_ID
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

_TG_API = "https://api.telegram.org/bot{token}/{method}"

_URL_RE = re.compile(
    r"https?://t\.me/"
    r"(?:(?P<username>[a-zA-Z0-9_]{5,})|c/(?P<chat_id>-?\d+))"
    r"/(?P<msg_id>\d+)"
)


def _parse_url(url: str):
    m = _URL_RE.match(url.strip())
    if not m:
        return None, None
    msg_id = int(m.group("msg_id"))
    if m.group("username"):
        return f"@{m.group('username')}", msg_id
    return int(m.group("chat_id")), msg_id


async def _tg_post(method: str, payload: dict) -> dict:
    """Raw Telegram Bot API POST via aiohttp."""
    url = _TG_API.format(token=BOT_TOKEN, method=method)
    async with aiohttp.ClientSession() as sess:
        async with sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            return await resp.json()


async def _get_reactors(chat_id, message_id: int) -> list[int]:
    """Paginate getMessageReactors, return list of user IDs."""
    user_ids: list[int] = []
    offset = 0
    limit  = 100

    while True:
        data = await _tg_post("getMessageReactors", {
            "chat_id":    str(chat_id),
            "message_id": message_id,
            "limit":      limit,
            "offset":     offset,
        })

        if not data.get("ok"):
            err = data.get("description", "unknown error")
            raise RuntimeError(err)

        reactors = data.get("result", [])
        if not reactors:
            break

        for r in reactors:
            # result is list of MessageReactor objects
            # MessageReactor has "type" and optional "user"
            if isinstance(r, dict):
                user_data = r.get("user")
                if user_data and isinstance(user_data, dict):
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


async def _check_caller_is_admin(bot: Bot, chat_id, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@router.message(Command("liketime"))
async def cmd_liketime(message: Message, bot: Bot) -> None:
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "📖 Использование:\n/liketime <ссылка на пост> <кол-во победителей>\n\n"
            "Пример: /liketime https://t.me/channel_name/123 3"
        )
        return

    url, count_str = parts[1], parts[2]
    if not count_str.isdigit() or int(count_str) < 1:
        await message.answer("⚠️ Количество победителей — целое число ≥ 1")
        return

    winners_count = int(count_str)
    chat_id, msg_id = _parse_url(url)

    if chat_id is None:
        await message.answer("❌ Ошибка ссылки\nФормат: https://t.me/channel_name/123")
        return

    # Verify caller is admin of that channel
    if not await _check_caller_is_admin(bot, chat_id, message.from_user.id):
        await message.answer("Нет доступа (вы не администратор этого канала)")
        return

    status_msg = await message.answer("⏳ Получаю список реакций...")

    try:
        raw_ids = await _get_reactors(chat_id, msg_id)
    except RuntimeError as e:
        await status_msg.edit_text(
            f"❌ Не удалось получить реакции\n\n"
            f"Убедитесь что:\n"
            f"• Бот является <b>администратором</b> канала\n"
            f"• Пост существует и содержит реакции\n\n"
            f"Ошибка: <code>{e}</code>",
            parse_mode="HTML",
        )
        return

    if not raw_ids:
        await status_msg.edit_text("❌ Нет участников (никто не поставил реакцию)")
        return

    unique_ids = list(set(raw_ids))
    await status_msg.edit_text(f"🔍 Реакций: {len(unique_ids)}. Проверяю подписки...")

    valid: list[int] = []
    for uid in unique_ids:
        if await _is_subscribed(bot, chat_id, uid):
            valid.append(uid)

    if not valid:
        await status_msg.edit_text("❌ Нет подписанных участников")
        return

    actual   = min(winners_count, len(valid))
    selected = random.sample(valid, actual)

    logger.info("Liketime draw | chat=%s | msg=%s | reactors=%s | valid=%s | winners=%s",
                chat_id, msg_id, len(unique_ids), len(valid), selected)

    # Send only IDs to moder group
    if MODER_GROUP_ID:
        ids_block = "\n".join(str(uid) for uid in selected)
        try:
            await bot.send_message(
                MODER_GROUP_ID,
                f"🎲 <b>Liketime победители</b>\n📎 {url}\n\n{ids_block}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send liketime to moder group | %s", e)

    ids_list = "\n".join(f"• <code>{uid}</code>" for uid in selected)
    await status_msg.edit_text(
        f"🎊 <b>Розыгрыш завершён</b>\n\n"
        f"👥 Участников (с подпиской): <b>{len(valid)}</b>\n"
        f"🏆 Победителей: <b>{actual}</b>\n\n"
        f"<b>Победители (ID):</b>\n{ids_list}",
        parse_mode="HTML",
    )

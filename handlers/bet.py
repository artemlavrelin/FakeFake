"""
/bet  — show all bet posts (all users)
/addbet — admin: add a new bet post (text + optional media)
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS
from database import repository
from states.contest import AddBetFSM
from keyboards.inline import cancel_keyboard
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ─── /bet ─────────────────────────────────────────────────────────────────────

@router.message(Command("bet"))
async def cmd_bet(message: Message, session: AsyncSession) -> None:
    posts = await repository.list_bet_posts(session, limit=10)
    if not posts:
        await message.answer("📢 Пока нет bet-постов.")
        return

    for post in reversed(posts):   # oldest first
        caption = f"📢 <b>NEW BET</b>\n\n{post.text}"
        try:
            if post.media_type == "photo" and post.media_id:
                await message.answer_photo(post.media_id, caption=caption, parse_mode="HTML")
            elif post.media_type == "video" and post.media_id:
                await message.answer_video(post.media_id, caption=caption, parse_mode="HTML")
            elif post.media_type == "document" and post.media_id:
                await message.answer_document(post.media_id, caption=caption, parse_mode="HTML")
            else:
                await message.answer(caption, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to send bet post %s | %s", post.id, e)
            await message.answer(caption, parse_mode="HTML")


# ─── /addbet ──────────────────────────────────────────────────────────────────

@router.message(Command("addbet"))
async def cmd_addbet(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    await state.set_state(AddBetFSM.waiting_content)
    await message.answer(
        "📢 <b>Создание bet-поста</b>\n\n"
        "Отправьте текст (можно с фото, видео или файлом).\n"
        "Медиа подпись = текст поста.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard("ru"),
    )


@router.message(AddBetFSM.waiting_content, F.text | F.photo | F.video | F.document)
async def fsm_addbet_content(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    await state.clear()

    text       = message.text or message.caption or ""
    media_id   = None
    media_type = None

    if message.photo:
        media_id   = message.photo[-1].file_id
        media_type = "photo"
        text       = message.caption or ""
    elif message.video:
        media_id   = message.video.file_id
        media_type = "video"
        text       = message.caption or ""
    elif message.document:
        media_id   = message.document.file_id
        media_type = "document"
        text       = message.caption or ""

    if not text and not media_id:
        await message.answer("⚠️ Нужен текст или медиафайл.")
        return

    post = await repository.create_bet_post(
        session, text=text, admin_id=message.from_user.id,
        media_id=media_id, media_type=media_type,
    )
    await message.answer(
        f"✅ Bet-пост <b>#{post.id}</b> опубликован.",
        parse_mode="HTML",
    )

"""
/social — show social media links.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import FACEBOOK_URL, INSTAGRAM_URL, THREADS_URL, TWITTER_URL
from keyboards.inline import social_keyboard

router = Router()


@router.message(Command("social"))
async def cmd_social(message: Message) -> None:
    await message.answer(
        "🌐 <b>Наши соцсети / Our socials</b>",
        parse_mode="HTML",
        reply_markup=social_keyboard(FACEBOOK_URL, TWITTER_URL, INSTAGRAM_URL, THREADS_URL),
    )

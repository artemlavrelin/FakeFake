"""
Drop every incoming update that is NOT from a private chat,
EXCEPT for inline callbacks that need to work from groups
(e.g. group_join: buttons in contest announcements).
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.logger import get_logger

logger = get_logger(__name__)

# Callback data prefixes that are allowed from non-private chats
_GROUP_CALLBACKS = ("group_join:",)


class PrivateChatOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat_type = None

        if isinstance(event, Message):
            chat_type = event.chat.type
        elif isinstance(event, CallbackQuery) and event.message:
            # Allow specific callbacks from groups (e.g. 🧲 Участвовать)
            cb_data = event.data or ""
            if any(cb_data.startswith(p) for p in _GROUP_CALLBACKS):
                return await handler(event, data)
            chat_type = event.message.chat.type

        if chat_type and chat_type != "private":
            logger.debug("Ignored non-private update | chat_type=%s", chat_type)
            return

        return await handler(event, data)

"""
Drop every incoming update that is NOT from a private chat.
The bot only handles user interactions in DMs.
Group messages (from users) are silently ignored.
The bot can still send proactive messages TO the group.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.logger import get_logger

logger = get_logger(__name__)


class PrivateChatOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Determine chat type
        chat_type = None
        if isinstance(event, Message):
            chat_type = event.chat.type
        elif isinstance(event, CallbackQuery) and event.message:
            chat_type = event.message.chat.type

        if chat_type and chat_type != "private":
            # Silently drop — bot doesn't respond in groups
            logger.debug("Ignored non-private update | chat_type=%s", chat_type)
            return

        return await handler(event, data)

"""
Throttle middleware: prevents callback spam by rate-limiting
per-user per-action. Uses a simple in-memory dict (sufficient
for single-instance bots; replace with Redis for multi-instance).
"""
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from utils.logger import get_logger

logger = get_logger(__name__)

# {user_id: {action: last_timestamp}}
_last_call: dict[int, dict[str, float]] = {}

# Seconds a user must wait between identical callback actions
THROTTLE_SECONDS = 2.0


class ThrottleMiddleware(BaseMiddleware):
    """
    Blocks repeated identical callback_data from the same user
    within THROTTLE_SECONDS window.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        user_id = event.from_user.id
        action = event.data or ""
        now = time.monotonic()

        user_calls = _last_call.setdefault(user_id, {})
        last = user_calls.get(action, 0.0)

        if now - last < THROTTLE_SECONDS:
            logger.debug(
                "Throttled callback | user=%s | action=%s | wait=%.1fs",
                user_id, action, THROTTLE_SECONDS - (now - last),
            )
            await event.answer("⏳ Пожалуйста, не нажимайте так быстро.", show_alert=False)
            return  # drop the event

        user_calls[action] = now
        return await handler(event, data)

"""
If a user sends any bot command (e.g. /start, /admin) while inside an FSM,
clear the state and let the command handlers process it normally.
Without this guard, FSM message handlers catch command text and produce
confusing responses like "Введите числовой ID конкурса:" after /start.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from utils.logger import get_logger

logger = get_logger(__name__)


class FsmCommandGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Only act on messages that look like bot commands
        text = event.text or ""
        if not text.startswith("/"):
            return await handler(event, data)

        state: FSMContext = data.get("state")
        if state is None:
            return await handler(event, data)

        current = await state.get_state()
        if current is not None:
            logger.debug(
                "Command received inside FSM — clearing state | user=%s | state=%s | cmd=%s",
                event.from_user.id, current, text.split()[0],
            )
            await state.clear()

        return await handler(event, data)

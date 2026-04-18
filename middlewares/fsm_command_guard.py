"""
Clears FSM state when a bot command is sent, so /start always works
regardless of what FSM state the user is currently in.
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

        text = event.text or ""
        if not text.startswith("/"):
            return await handler(event, data)

        try:
            state: FSMContext = data.get("state")
            if state is not None:
                current = await state.get_state()
                if current is not None:
                    logger.debug(
                        "FSM cleared by command | user=%s | state=%s | cmd=%s",
                        event.from_user.id, current, text.split()[0],
                    )
                    await state.clear()
        except Exception as e:
            logger.warning("FsmCommandGuard error (non-fatal) | %s", e)

        return await handler(event, data)

import asyncio
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, REDIS_URL, USE_WEBHOOK, WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_PATH, WEBHOOK_URL
from database import init_db
from handlers import admin, user
from middlewares.db import DbSessionMiddleware
from middlewares.private_only import PrivateChatOnlyMiddleware
from middlewares.throttle import ThrottleMiddleware
from utils.logger import get_logger, setup_logging

setup_logging(to_file=os.getenv("LOG_TO_FILE", "0") == "1")
logger = get_logger(__name__)


def build_storage():
    if REDIS_URL:
        logger.info("FSM: Redis")
        return RedisStorage.from_url(REDIS_URL)
    logger.info("FSM: MemoryStorage")
    return MemoryStorage()


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=build_storage())

    # 1. Drop non-private chats first — cheapest check
    dp.message.middleware(PrivateChatOnlyMiddleware())
    dp.callback_query.middleware(PrivateChatOnlyMiddleware())

    # 2. Throttle callback spam
    dp.callback_query.middleware(ThrottleMiddleware())

    # 3. DB session
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    dp.include_router(admin.router)
    dp.include_router(user.router)
    return dp


async def on_startup(bot: Bot) -> None:
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook: %s", WEBHOOK_URL)


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()


def run_webhook() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # webhook path строго с токеном
    webhook_path = f"/webhook/{BOT_TOKEN}"

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=webhook_path)

    setup_application(app, dp, bot=bot)

    logger.info("Webhook server: %s:%s", WEBAPP_HOST, WEBAPP_PORT)
    logger.info("Webhook path: %s", webhook_path)

    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


async def run_polling() -> None:
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    dp = build_dispatcher()
    logger.info("Polling started.")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logger.info("ContestBot v4 | mode=%s", "WEBHOOK" if USE_WEBHOOK else "POLLING")
    if USE_WEBHOOK:
        run_webhook()
    else:
        asyncio.run(run_polling())

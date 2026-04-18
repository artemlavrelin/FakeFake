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
from database.engine import init_db
from middlewares.db import DbSessionMiddleware
from middlewares.fsm_command_guard import FsmCommandGuardMiddleware
from middlewares.private_only import PrivateChatOnlyMiddleware
from middlewares.throttle import ThrottleMiddleware
from scheduler import create_scheduler
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
    from handlers.user         import router as user_router
    from handlers.loot         import router as loot_router
    from handlers.liketime     import router as liketime_router
    from handlers.social       import router as social_router
    from handlers.slot         import router as slot_router
    from handlers.bet          import router as bet_router
    from handlers.profile      import router as profile_router
    from handlers.payments     import router as payments_router
    from handlers.tasks_admin  import router as tasks_admin_router
    from handlers.tasks_user   import router as tasks_user_router
    from handlers.admin_stats  import router as admin_stats_router
    from handlers.admin        import router as admin_router

    dp = Dispatcher(storage=build_storage())
    dp.message.middleware(PrivateChatOnlyMiddleware())
    dp.callback_query.middleware(PrivateChatOnlyMiddleware())
    dp.message.middleware(FsmCommandGuardMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # Order matters — user first for cancel_fsm/menu
    dp.include_router(user_router)
    dp.include_router(profile_router)
    dp.include_router(payments_router)
    dp.include_router(tasks_user_router)
    dp.include_router(tasks_admin_router)
    dp.include_router(loot_router)
    dp.include_router(slot_router)
    dp.include_router(bet_router)
    dp.include_router(liketime_router)
    dp.include_router(social_router)
    dp.include_router(admin_stats_router)
    dp.include_router(admin_router)
    return dp


async def on_startup(bot: Bot) -> None:
    await init_db()
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook: %s", WEBHOOK_URL)


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()


def run_webhook() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp  = build_dispatcher()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    logger.info("Webhook server: %s:%s", WEBAPP_HOST, WEBAPP_PORT)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


async def run_polling() -> None:
    await init_db()
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    dp  = build_dispatcher()
    logger.info("Polling started.")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    logger.info("ContestBot v11 | mode=%s", "WEBHOOK" if USE_WEBHOOK else "POLLING")
    if USE_WEBHOOK:
        run_webhook()
    else:
        asyncio.run(run_polling())

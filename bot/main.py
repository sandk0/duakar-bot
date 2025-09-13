import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from bot.config import settings
from database.connection import init_db, close_db, redis_client
from bot.handlers import (
    start_handler,
    subscription_handler,
    payment_handler,
    config_handler,
    referral_handler,
    support_handler,
    test_handler,
    stats_handler,
    faq_handler,
    settings_handler
)
from bot.handlers import admin_simple
from bot.middleware.auth import AuthMiddleware
from bot.middleware.throttling import ThrottlingMiddleware
from bot.middleware.logging import LoggingMiddleware
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry if configured
if settings.sentry_dsn and settings.sentry_dsn.strip() and settings.sentry_dsn.startswith(('http://', 'https://')):
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[sentry_logging],
        traces_sample_rate=1.0,
        environment="development" if settings.debug else "production"
    )
else:
    logger.info("Sentry monitoring is disabled")


async def on_startup(bot: Bot):
    """Actions to perform on bot startup"""
    logger.info("Starting bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Set bot commands
    from bot.utils.commands import set_bot_commands, set_admin_commands
    await set_bot_commands(bot)
    # Set admin commands for the admin user
    await set_admin_commands(bot, 17499218)  # Your telegram ID
    logger.info("Bot commands set")
    
    # Notify admins about bot start
    # await notify_admins(bot, "Bot started successfully!")
    
    logger.info("Bot started successfully")


async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown"""
    logger.info("Shutting down bot...")
    
    # Close database connections
    await close_db()
    
    # Close bot session
    await bot.session.close()
    
    logger.info("Bot shut down successfully")


async def main():
    """Main function to run the bot"""
    # Initialize bot and dispatcher
    bot = Bot(token=settings.bot_token)
    
    # Use Redis for FSM storage
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage)
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Register middlewares - ВРЕМЕННО ОТКЛЮЧЕНЫ ДЛЯ ОТЛАДКИ
    # AuthMiddleware отключен - хендлеры теперь создают собственные сессии
    #dp.message.middleware(ThrottlingMiddleware())
    #dp.message.middleware(LoggingMiddleware())
    #dp.callback_query.middleware(ThrottlingMiddleware())
    #dp.callback_query.middleware(LoggingMiddleware())
    
    # Temporary fix - remove after config_handler is fixed
    # @dp.callback_query()
    # async def test_callback_handler(callback):
    #     logger.info(f"MAIN.PY DEBUG: Got callback {callback.data}")
    #     if callback.data in ["copy_link", "show_qr"]:
    #         logger.info(f"MAIN.PY: Found target callback {callback.data}")
    #         await callback.answer(f"MAIN.PY caught: {callback.data}")
    #         return True  # Stop propagation to other handlers
    #     # Let other handlers process it
    
    # Register handlers - config_handler первый для отладки
    dp.include_router(config_handler.router)
    dp.include_router(start_handler.router)
    dp.include_router(test_handler.router)
    dp.include_router(subscription_handler.router)
    dp.include_router(payment_handler.router)
    dp.include_router(referral_handler.router)
    dp.include_router(support_handler.router)
    dp.include_router(stats_handler.router)
    dp.include_router(faq_handler.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin_simple.router)
    
    # Start polling
    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
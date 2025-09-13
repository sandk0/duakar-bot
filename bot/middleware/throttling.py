from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.connection import redis_client
from bot.config import settings
import time
import logging

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting"""
    
    def __init__(self, rate_limit: int = 10, time_window: int = 60):
        self.rate_limit = rate_limit  # Max requests
        self.time_window = time_window  # Time window in seconds
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Get user ID
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        else:
            return await handler(event, data)
        
        if not user_id:
            return await handler(event, data)
        
        # Skip rate limiting for admin users
        admin_user_ids = [17499218]  # Добавьте сюда ID администраторов
        if user_id in admin_user_ids:
            return await handler(event, data)
        
        # Create Redis key for rate limiting
        key = f"throttle:{user_id}"
        
        # Get current request count
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.time_window)
        result = await pipe.execute()
        request_count = result[0]
        
        # Check if rate limit exceeded
        if request_count > self.rate_limit:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Слишком много запросов. Пожалуйста, подождите немного."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Слишком много запросов. Подождите немного.",
                    show_alert=True
                )
            return
        
        return await handler(event, data)
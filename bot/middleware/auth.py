from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.connection import async_session_maker
from database.models import User
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Simplified middleware that just provides user_id and database session"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        if isinstance(event, Message):
            user_data = event.from_user
        elif isinstance(event, CallbackQuery):
            user_data = event.from_user
        else:
            return await handler(event, data)
        
        if not user_data:
            return await handler(event, data)
        
        # Create database session
        session = async_session_maker()
        try:
            # Add telegram user data and session to data
            data["telegram_user_id"] = user_data.id
            data["telegram_username"] = user_data.username
            data["telegram_first_name"] = user_data.first_name
            data["telegram_last_name"] = user_data.last_name
            data["session"] = session
            
            # Call handler
            result = await handler(event, data)
            return result
            
        finally:
            await session.close()
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging user actions"""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Get event type and user info
        event_type = None
        user_id = None
        event_data = {}
        
        if isinstance(event, Message):
            event_type = "message"
            user_id = event.from_user.id if event.from_user else None
            event_data = {
                "text": event.text[:100] if event.text else None,
                "chat_id": event.chat.id,
                "message_id": event.message_id
            }
        elif isinstance(event, CallbackQuery):
            event_type = "callback_query"
            user_id = event.from_user.id if event.from_user else None
            event_data = {
                "data": event.data,
                "message_id": event.message.message_id if event.message else None
            }
        
        # Log the event
        if event_type and user_id:
            logger.info(
                f"User {user_id} - {event_type}: {json.dumps(event_data, ensure_ascii=False)}"
            )
            
        # Debug log for callback queries
        if isinstance(event, CallbackQuery):
            logger.info(f"CALLBACK DEBUG: data={event.data}, user={user_id}")
        
        # Process the event
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                f"Error processing {event_type} from user {user_id}: {str(e)}",
                exc_info=True
            )
            
            # Send error message to user
            if isinstance(event, Message):
                await event.answer(
                    f"❌ Произошла ошибка при обработке запроса: {str(e)}"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"❌ Произошла ошибка: {str(e)}",
                    show_alert=True
                )
            
            raise
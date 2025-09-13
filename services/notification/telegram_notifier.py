import logging
from typing import Dict, Any, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.config import settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification service"""
    
    def __init__(self):
        self.bot = Bot(token=settings.bot_token)
    
    async def send_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> bool:
        """Send notification via Telegram"""
        try:
            # Format message with title
            full_message = f"*{title}*\n\n{message}"
            
            # Add keyboard if needed
            reply_markup = None
            if data and 'keyboard' in data:
                reply_markup = data['keyboard']
            
            await self.bot.send_message(
                chat_id=user_id,
                text=full_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            return True
            
        except TelegramForbiddenError:
            # User blocked the bot
            logger.warning(f"User {user_id} has blocked the bot")
            return False
            
        except TelegramBadRequest as e:
            # Invalid user ID or other Telegram error
            logger.error(f"Telegram error for user {user_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification to user {user_id}: {e}")
            return False
    
    async def send_subscription_expiry_warning(
        self,
        user_id: int,
        days_remaining: int
    ) -> bool:
        """Send subscription expiry warning"""
        if days_remaining <= 0:
            title = "🚨 Подписка истекла"
            message = ("Ваша подписка на VPN истекла.\n\n"
                      "Для продолжения использования сервиса продлите подписку.")
        elif days_remaining == 1:
            title = "⚠️ Подписка истекает завтра"
            message = ("Ваша подписка на VPN истекает завтра.\n\n"
                      "Не забудьте продлить подписку, чтобы не потерять доступ к сервису.")
        else:
            title = "⏰ Подписка скоро истекает"
            message = (f"Ваша подписка на VPN истекает через {days_remaining} дней.\n\n"
                      "Рекомендуем продлить подписку заранее.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_payment_success_notification(
        self,
        user_id: int,
        amount: float,
        currency: str = 'RUB'
    ) -> bool:
        """Send payment success notification"""
        title = "✅ Платеж успешно обработан"
        message = (f"Ваш платеж на сумму {amount} {currency} успешно обработан.\n\n"
                  "Подписка активирована. Можете получить новую конфигурацию VPN.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_payment_failed_notification(
        self,
        user_id: int,
        amount: float,
        currency: str = 'RUB'
    ) -> bool:
        """Send payment failed notification"""
        title = "❌ Ошибка обработки платежа"
        message = (f"Не удалось обработать ваш платеж на сумму {amount} {currency}.\n\n"
                  "Попробуйте еще раз или обратитесь в поддержку.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_config_regenerated_notification(
        self,
        user_id: int
    ) -> bool:
        """Send VPN config regenerated notification"""
        title = "🔄 Конфигурация обновлена"
        message = ("Ваша VPN конфигурация была обновлена.\n\n"
                  "Используйте команду /config для получения новой конфигурации.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_referral_bonus_notification(
        self,
        user_id: int,
        bonus_days: int,
        referred_user_name: str = None
    ) -> bool:
        """Send referral bonus notification"""
        title = "🎉 Реферальный бонус получен!"
        
        if referred_user_name:
            message = (f"Пользователь {referred_user_name} зарегистрировался по вашей реферальной ссылке.\n\n"
                      f"Вы получили {bonus_days} дней подписки в подарок!")
        else:
            message = f"Вы получили {bonus_days} дней подписки в подарок за приглашение друга!"
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_trial_activation_notification(
        self,
        user_id: int
    ) -> bool:
        """Send trial activation notification"""
        title = "🎯 Пробный период активирован"
        message = ("Ваш пробный период на 7 дней успешно активирован!\n\n"
                  "Используйте команду /config для получения конфигурации VPN.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_admin_notification(
        self,
        admin_user_id: int,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> bool:
        """Send notification to admin"""
        admin_title = f"🔧 [АДМИН] {title}"
        return await self.send_notification(
            user_id=admin_user_id,
            title=admin_title,
            message=message,
            data=data
        )
    
    async def send_system_alert(
        self,
        admin_user_ids: list,
        alert_type: str,
        message: str
    ) -> int:
        """Send system alert to admins"""
        title = f"🚨 Системное уведомление: {alert_type}"
        success_count = 0
        
        for admin_id in admin_user_ids:
            try:
                success = await self.send_admin_notification(
                    admin_user_id=admin_id,
                    title=title,
                    message=message
                )
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_id}: {e}")
        
        return success_count
    
    async def close(self):
        """Close bot session"""
        try:
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"Error closing Telegram notifier: {e}")
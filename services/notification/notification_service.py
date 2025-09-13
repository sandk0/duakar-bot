import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from .telegram_notifier import TelegramNotifier
from .email_notifier import EmailNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    """Centralized notification service"""
    
    def __init__(self):
        self.telegram_notifier = TelegramNotifier()
        self.email_notifier = EmailNotifier()
        self.notification_types = {
            'subscription_expiry': {
                'title': 'Подписка истекает',
                'template': 'Ваша подписка истекает через {days} дней'
            },
            'subscription_expired': {
                'title': 'Подписка истекла',
                'template': 'Ваша подписка истекла. Продлите подписку для продолжения использования VPN'
            },
            'payment_success': {
                'title': 'Платеж успешен',
                'template': 'Платеж на сумму {amount} {currency} успешно обработан'
            },
            'payment_failed': {
                'title': 'Ошибка платежа',
                'template': 'Не удалось обработать платеж на сумму {amount} {currency}'
            },
            'config_regenerated': {
                'title': 'Конфигурация обновлена',
                'template': 'Ваша VPN конфигурация была обновлена'
            },
            'referral_bonus': {
                'title': 'Реферальный бонус',
                'template': 'Вы получили {days} дней за приглашение друга!'
            },
            'trial_started': {
                'title': 'Пробный период активирован',
                'template': 'Ваш пробный период на 7 дней активирован'
            },
            'system_maintenance': {
                'title': 'Техническое обслуживание',
                'template': 'Планируется техническое обслуживание с {start_time} до {end_time}'
            }
        }
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: str,
        data: Dict[str, Any] = None,
        session: Optional[AsyncSession] = None,
        channels: List[str] = None
    ) -> bool:
        """Send notification to user"""
        try:
            if notification_type not in self.notification_types:
                logger.error(f"Unknown notification type: {notification_type}")
                return False
            
            template_info = self.notification_types[notification_type]
            title = template_info['title']
            message = template_info['template']
            
            if data:
                message = message.format(**data)
            
            # Default to Telegram if no channels specified
            if channels is None:
                channels = ['telegram']
            
            success = True
            
            # Send via Telegram
            if 'telegram' in channels:
                try:
                    await self.telegram_notifier.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        data=data
                    )
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification to user {user_id}: {e}")
                    success = False
            
            # Send via Email (if email is available)
            if 'email' in channels:
                try:
                    await self.email_notifier.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        data=data
                    )
                except Exception as e:
                    logger.error(f"Failed to send email notification to user {user_id}: {e}")
                    success = False
            
            # Store notification in database (TODO: Create Notification model)
            # if session:
            #     try:
            #         notification = Notification(
            #             user_id=user_id,
            #             type=notification_type,
            #             title=title,
            #             message=message,
            #             data=data,
            #             channels=channels,
            #             sent_at=datetime.utcnow() if success else None,
            #             status='sent' if success else 'failed'
            #         )
            #         session.add(notification)
            #         await session.commit()
            #     except Exception as e:
            #         logger.error(f"Failed to store notification in database: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_bulk_notification(
        self,
        user_ids: List[int],
        notification_type: str,
        data: Dict[str, Any] = None,
        session: Optional[AsyncSession] = None,
        channels: List[str] = None,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Send notification to multiple users"""
        results = {'success': 0, 'failed': 0}
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            tasks = []
            
            for user_id in batch:
                task = self.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    data=data,
                    session=session,
                    channels=channels
                )
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results['failed'] += 1
                elif result:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        logger.info(f"Bulk notification results: {results}")
        return results
    
    async def send_expiry_warnings(self, session: AsyncSession, days_before: int = 3):
        """Send subscription expiry warnings"""
        from sqlalchemy import select, and_
        from datetime import timedelta
        from database.models import Subscription
        
        target_date = datetime.utcnow() + timedelta(days=days_before)
        
        # Find subscriptions expiring soon
        result = await session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == 'active',
                    Subscription.end_date <= target_date,
                    Subscription.end_date > datetime.utcnow()
                )
            )
        )
        
        expiring_subscriptions = result.scalars().all()
        
        for subscription in expiring_subscriptions:
            remaining_days = (subscription.end_date - datetime.utcnow()).days
            
            await self.send_notification(
                user_id=subscription.user_id,
                notification_type='subscription_expiry',
                data={'days': remaining_days},
                session=session
            )
    
    async def send_payment_notification(
        self,
        user_id: int,
        payment_status: str,
        amount: float,
        currency: str = 'RUB',
        session: Optional[AsyncSession] = None
    ):
        """Send payment status notification"""
        notification_type = 'payment_success' if payment_status == 'completed' else 'payment_failed'
        
        await self.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            data={
                'amount': amount,
                'currency': currency
            },
            session=session
        )
    
    async def send_referral_bonus_notification(
        self,
        user_id: int,
        bonus_days: int,
        session: Optional[AsyncSession] = None
    ):
        """Send referral bonus notification"""
        await self.send_notification(
            user_id=user_id,
            notification_type='referral_bonus',
            data={'days': bonus_days},
            session=session
        )
    
    async def send_system_maintenance_notification(
        self,
        user_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        session: Optional[AsyncSession] = None
    ):
        """Send system maintenance notification to users"""
        await self.send_bulk_notification(
            user_ids=user_ids,
            notification_type='system_maintenance',
            data={
                'start_time': start_time.strftime('%d.%m.%Y %H:%M'),
                'end_time': end_time.strftime('%d.%m.%Y %H:%M')
            },
            session=session
        )
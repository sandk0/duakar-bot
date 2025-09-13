from celery import shared_task
from database.connection import async_session_maker
from database.models import User, Subscription, SubscriptionStatus
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from aiogram import Bot
from bot.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


async def send_notification_to_user(bot: Bot, user_id: int, message: str):
    """Send notification to specific user"""
    try:
        await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        logger.info(f"Notification sent to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")
        return False


@shared_task(bind=True)
def check_expiring_subscriptions(self):
    """Check for expiring subscriptions and send notifications"""
    return asyncio.run(_check_expiring_subscriptions())


async def _check_expiring_subscriptions():
    """Async implementation of subscription expiration check"""
    bot = Bot(token=settings.bot_token)
    
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            notification_days = settings.notification_days_before_expiry  # [1, 2, 3]
            
            for days_before in notification_days:
                # Calculate target date
                target_date = now + timedelta(days=days_before)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Get subscriptions expiring on target date
                result = await session.execute(
                    select(Subscription, User)
                    .join(User, Subscription.user_id == User.id)
                    .where(
                        and_(
                            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                            Subscription.end_date >= start_of_day,
                            Subscription.end_date <= end_of_day,
                            User.is_blocked == False
                        )
                    )
                )
                
                expiring_subs = result.all()
                
                for subscription, user in expiring_subs:
                    # Prepare notification message
                    if days_before == 1:
                        message = (
                            f"⏰ **Подписка истекает завтра!**\n\n"
                            f"Ваша VPN подписка истекает завтра "
                            f"({subscription.end_date.strftime('%d.%m.%Y')}).\n\n"
                            f"💳 Продлите подписку, чтобы не потерять доступ к VPN.\n"
                            f"Используйте команду /pay или кнопку 'Оплатить/Продлить'"
                        )
                    elif days_before == 2:
                        message = (
                            f"⏰ **Подписка истекает через 2 дня**\n\n"
                            f"Ваша VPN подписка истекает "
                            f"{subscription.end_date.strftime('%d.%m.%Y')}.\n\n"
                            f"Не забудьте продлить подписку заранее!"
                        )
                    else:
                        message = (
                            f"⏰ **Подписка истекает через {days_before} дня**\n\n"
                            f"Ваша VPN подписка истекает "
                            f"{subscription.end_date.strftime('%d.%m.%Y')}.\n\n"
                            f"Рекомендуем продлить подписку заранее."
                        )
                    
                    # Send notification
                    await send_notification_to_user(bot, user.telegram_id, message)
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                
                logger.info(f"Processed {len(expiring_subs)} subscriptions expiring in {days_before} days")
            
            # Check and disable expired subscriptions
            await _disable_expired_subscriptions(session, bot)
            
    except Exception as e:
        logger.error(f"Error in check_expiring_subscriptions: {e}")
        raise
    finally:
        await bot.session.close()


async def _disable_expired_subscriptions(session, bot: Bot):
    """Disable expired subscriptions"""
    now = datetime.now()
    
    # Get expired subscriptions
    result = await session.execute(
        select(Subscription, User)
        .join(User, Subscription.user_id == User.id)
        .where(
            and_(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                Subscription.end_date < now,
                User.is_blocked == False
            )
        )
    )
    
    expired_subs = result.all()
    
    for subscription, user in expired_subs:
        # Update subscription status
        subscription.status = SubscriptionStatus.EXPIRED
        
        # Disable VPN config in Marzban
        try:
            from services.marzban import marzban_client, UserStatus
            from database.models import VPNConfig
            
            # Get VPN config
            vpn_result = await session.execute(
                select(VPNConfig).where(VPNConfig.user_id == user.id)
            )
            vpn_config = vpn_result.scalar_one_or_none()
            
            if vpn_config and vpn_config.marzban_user_id:
                async with marzban_client as client:
                    await client.update_user(
                        username=vpn_config.marzban_user_id,
                        status=UserStatus.DISABLED
                    )
                vpn_config.is_active = False
                logger.info(f"Disabled VPN for user {user.telegram_id}")
        
        except Exception as e:
            logger.error(f"Failed to disable VPN for user {user.telegram_id}: {e}")
        
        # Send expiration notification
        message = (
            f"❌ **Подписка истекла**\n\n"
            f"Ваша VPN подписка истекла.\n"
            f"Доступ к VPN временно приостановлен.\n\n"
            f"💳 Продлите подписку для восстановления доступа.\n"
            f"Используйте команду /pay"
        )
        
        await send_notification_to_user(bot, user.telegram_id, message)
    
    if expired_subs:
        await session.commit()
        logger.info(f"Disabled {len(expired_subs)} expired subscriptions")


@shared_task(bind=True)
def send_broadcast_message(self, message_id: int):
    """Send broadcast message to users"""
    return asyncio.run(_send_broadcast_message(message_id))


async def _send_broadcast_message(message_id: int):
    """Async implementation of broadcast message sending"""
    bot = Bot(token=settings.bot_token)
    
    try:
        async with async_session_maker() as session:
            from database.models import BroadcastMessage
            
            # Get broadcast message
            result = await session.execute(
                select(BroadcastMessage).where(BroadcastMessage.id == message_id)
            )
            broadcast = result.scalar_one_or_none()
            
            if not broadcast:
                logger.error(f"Broadcast message {message_id} not found")
                return
            
            # Update status
            broadcast.status = "in_progress"
            await session.commit()
            
            # Get target users based on audience
            if broadcast.target_audience == "all":
                user_query = select(User).where(User.is_blocked == False)
            elif broadcast.target_audience == "active":
                user_query = (
                    select(User)
                    .join(Subscription, User.id == Subscription.user_id)
                    .where(
                        and_(
                            User.is_blocked == False,
                            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                        )
                    )
                )
            elif broadcast.target_audience == "expired":
                user_query = (
                    select(User)
                    .join(Subscription, User.id == Subscription.user_id)
                    .where(
                        and_(
                            User.is_blocked == False,
                            Subscription.status == SubscriptionStatus.EXPIRED
                        )
                    )
                )
            else:
                user_query = select(User).where(User.is_blocked == False)
            
            result = await session.execute(user_query)
            users = result.scalars().all()
            
            broadcast.total_recipients = len(users)
            await session.commit()
            
            # Send messages
            sent_count = 0
            failed_count = 0
            
            for user in users:
                try:
                    success = await send_notification_to_user(
                        bot, user.telegram_id, broadcast.content
                    )
                    
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                    
                    # Update progress every 10 messages
                    if (sent_count + failed_count) % 10 == 0:
                        broadcast.sent_count = sent_count
                        broadcast.failed_count = failed_count
                        await session.commit()
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)  # 20 messages per second
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to send broadcast to user {user.telegram_id}: {e}")
            
            # Update final status
            broadcast.sent_count = sent_count
            broadcast.failed_count = failed_count
            broadcast.status = "completed"
            broadcast.completed_at = datetime.now()
            
            await session.commit()
            
            logger.info(f"Broadcast {message_id} completed: {sent_count} sent, {failed_count} failed")
            
    except Exception as e:
        logger.error(f"Error in send_broadcast_message: {e}")
        # Mark as failed
        async with async_session_maker() as session:
            from database.models import BroadcastMessage
            result = await session.execute(
                select(BroadcastMessage).where(BroadcastMessage.id == message_id)
            )
            broadcast = result.scalar_one_or_none()
            if broadcast:
                broadcast.status = "failed"
                await session.commit()
        raise
    finally:
        await bot.session.close()


@shared_task(bind=True)
def send_payment_success_notification(self, user_id: int, subscription_data: dict):
    """Send payment success notification"""
    return asyncio.run(_send_payment_success_notification(user_id, subscription_data))


async def _send_payment_success_notification(user_id: int, subscription_data: dict):
    """Send payment success notification to user"""
    bot = Bot(token=settings.bot_token)
    
    try:
        plan_name = subscription_data.get('plan_type', 'подписка')
        days = subscription_data.get('days', 30)
        amount = subscription_data.get('amount', '0')
        
        message = (
            f"✅ **Оплата прошла успешно!**\n\n"
            f"💳 Тариф: {plan_name}\n"
            f"📅 Период: {days} дней\n"
            f"💰 Сумма: {amount} ₽\n\n"
            f"🔑 Ваша VPN подписка активирована!\n"
            f"Получите конфигурацию: /config"
        )
        
        await send_notification_to_user(bot, user_id, message)
        
    except Exception as e:
        logger.error(f"Error sending payment success notification: {e}")
        raise
    finally:
        await bot.session.close()
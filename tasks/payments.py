from celery import shared_task
from database.connection import async_session_maker
from database.models import Payment, User, Subscription, VPNConfig, SubscriptionStatus
from database.models.payment import PaymentStatus
from services.payment import payment_manager
from services.marzban import marzban_client, generate_unique_username
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_payment_webhook(self, payment_data: dict, provider_name: str):
    """Process payment webhook from provider"""
    return asyncio.run(_process_payment_webhook(payment_data, provider_name))


async def _process_payment_webhook(payment_data: dict, provider_name: str):
    """Async implementation of payment webhook processing"""
    try:
        # Parse webhook data
        callback = payment_manager.parse_webhook(provider_name, payment_data)
        
        async with async_session_maker() as session:
            # Find payment in database
            result = await session.execute(
                select(Payment).where(Payment.external_payment_id == callback.payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.error(f"Payment {callback.payment_id} not found in database")
                return False
            
            # Update payment status
            old_status = payment.status
            payment.status = callback.status.value
            
            # If payment successful and status changed
            if (callback.status.value == PaymentStatus.SUCCESS and 
                old_status != PaymentStatus.SUCCESS):
                
                await _activate_subscription_for_payment(payment, session)
            
            await session.commit()
            logger.info(f"Payment {payment.id} status updated: {old_status} -> {payment.status}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}")
        raise


async def _activate_subscription_for_payment(payment: Payment, session):
    """Activate subscription after successful payment"""
    try:
        # Get user
        result = await session.execute(
            select(User).where(User.id == payment.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {payment.user_id} not found")
            return
        
        # Parse metadata from payment
        metadata = payment.metadata or "{}"
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        plan_type = metadata.get('plan_type', 'monthly')
        days = int(metadata.get('days', 30))
        
        # Get current active subscription
        result = await session.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user.id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                )
            )
            .order_by(Subscription.created_at.desc())
        )
        current_subscription = result.scalar_one_or_none()
        
        # Calculate new dates
        now = datetime.now()
        if current_subscription and current_subscription.end_date > now:
            # Extend existing subscription
            start_date = current_subscription.end_date
            end_date = start_date + timedelta(days=days)
            current_subscription.end_date = end_date
            new_subscription = current_subscription
            logger.info(f"Extended subscription for user {user.telegram_id}")
        else:
            # Create new subscription
            start_date = now
            end_date = now + timedelta(days=days)
            
            # Deactivate old subscriptions
            if current_subscription:
                current_subscription.status = SubscriptionStatus.EXPIRED
            
            # Create new subscription
            new_subscription = Subscription(
                user_id=user.id,
                plan_type=plan_type,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                is_trial=False,
                auto_renewal=True
            )
            session.add(new_subscription)
            logger.info(f"Created new subscription for user {user.telegram_id}")
        
        # Link payment to subscription
        payment.subscription_id = new_subscription.id
        
        # Activate or create VPN config
        await _ensure_vpn_config_active(user, session)
        
        # Process referral bonus if applicable
        if user.referrer_id:
            await _process_referral_bonus(user.referrer_id, user.id, session)
        
        # Send success notification
        from tasks.notifications import send_payment_success_notification
        send_payment_success_notification.delay(
            user_id=user.telegram_id,
            subscription_data={
                'plan_type': plan_type,
                'days': days,
                'amount': str(payment.amount)
            }
        )
        
    except Exception as e:
        logger.error(f"Error activating subscription for payment {payment.id}: {e}")
        raise


async def _ensure_vpn_config_active(user: User, session):
    """Ensure user has active VPN configuration"""
    try:
        # Get existing VPN config
        result = await session.execute(
            select(VPNConfig).where(VPNConfig.user_id == user.id)
        )
        vpn_config = result.scalar_one_or_none()
        
        if vpn_config:
            # Reactivate existing config
            vpn_config.is_active = True
            
            # Update Marzban user status
            async with marzban_client as client:
                from services.marzban import UserStatus
                await client.update_user(
                    username=vpn_config.marzban_user_id,
                    status=UserStatus.ACTIVE
                )
            
            logger.info(f"Reactivated VPN config for user {user.telegram_id}")
        
        else:
            # Create new VPN config
            async with marzban_client as client:
                marzban_username = generate_unique_username(user.telegram_id)
                marzban_user = await client.create_user(
                    username=marzban_username,
                    note=f"User: {user.telegram_id}"
                )
                
                # Save VPN config
                vpn_config = VPNConfig(
                    user_id=user.id,
                    marzban_user_id=marzban_username,
                    config_url=marzban_user.links[0] if marzban_user.links else None,
                    is_active=True
                )
                session.add(vpn_config)
            
            logger.info(f"Created VPN config for user {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error ensuring VPN config for user {user.telegram_id}: {e}")
        raise


async def _process_referral_bonus(referrer_id: int, referral_id: int, session):
    """Process referral bonus after successful payment"""
    try:
        from database.models import ReferralStat
        from bot.config import settings
        
        # Get referrer's stats
        result = await session.execute(
            select(ReferralStat).where(ReferralStat.user_id == referrer_id)
        )
        referral_stat = result.scalar_one_or_none()
        
        if not referral_stat:
            referral_stat = ReferralStat(user_id=referrer_id)
            session.add(referral_stat)
        
        # Add bonus days
        referral_stat.bonus_days_earned += settings.referral_bonus_days
        
        logger.info(f"Added {settings.referral_bonus_days} referral bonus days to user {referrer_id}")
        
    except Exception as e:
        logger.error(f"Error processing referral bonus: {e}")


@shared_task(bind=True)
def retry_failed_payments(self):
    """Retry failed auto-renewal payments"""
    return asyncio.run(_retry_failed_payments())


async def _retry_failed_payments():
    """Async implementation of failed payment retry"""
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            
            # Get subscriptions that should auto-renew but failed
            result = await session.execute(
                select(Subscription, User)
                .join(User, Subscription.user_id == User.id)
                .where(
                    and_(
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        Subscription.auto_renewal == True,
                        Subscription.end_date >= now - timedelta(days=2),  # Within last 2 days
                        User.is_blocked == False
                    )
                )
            )
            
            failed_renewals = result.all()
            
            for subscription, user in failed_renewals:
                # Check if there's a recent failed payment
                result = await session.execute(
                    select(Payment)
                    .where(
                        and_(
                            Payment.user_id == user.id,
                            Payment.status == PaymentStatus.FAILED,
                            Payment.created_at >= now - timedelta(days=2)
                        )
                    )
                    .order_by(Payment.created_at.desc())
                )
                
                failed_payment = result.scalar_one_or_none()
                
                if failed_payment:
                    # Try to retry the payment (implementation depends on provider)
                    logger.info(f"Found failed renewal for user {user.telegram_id}, payment {failed_payment.id}")
                    
                    # For now, just send notification about renewal failure
                    from tasks.notifications import send_notification_to_user
                    from aiogram import Bot
                    
                    bot = Bot(token=settings.bot_token)
                    message = (
                        f"❌ **Не удалось продлить подписку**\n\n"
                        f"При автоматическом продлении подписки произошла ошибка.\n"
                        f"Пожалуйста, проверьте способ оплаты и продлите подписку вручную.\n\n"
                        f"💳 Для продления используйте команду /pay"
                    )
                    
                    await send_notification_to_user(bot, user.telegram_id, message)
                    await bot.session.close()
            
            logger.info(f"Processed {len(failed_renewals)} failed auto-renewals")
            
    except Exception as e:
        logger.error(f"Error in retry_failed_payments: {e}")
        raise


@shared_task(bind=True)
def cleanup_pending_payments(self):
    """Cleanup old pending payments"""
    return asyncio.run(_cleanup_pending_payments())


async def _cleanup_pending_payments():
    """Async implementation of pending payments cleanup"""
    try:
        async with async_session_maker() as session:
            # Cancel payments that are pending for more than 1 hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            result = await session.execute(
                select(Payment)
                .where(
                    and_(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.created_at < cutoff_time
                    )
                )
            )
            
            old_payments = result.scalars().all()
            
            for payment in old_payments:
                # Try to get actual status from payment provider
                if payment.payment_system and payment.external_payment_id:
                    try:
                        actual_status = await payment_manager.get_payment_status(
                            payment.external_payment_id,
                            payment.payment_system
                        )
                        payment.status = actual_status.value
                        
                        if actual_status.value == PaymentStatus.SUCCESS:
                            await _activate_subscription_for_payment(payment, session)
                    
                    except Exception as e:
                        logger.error(f"Error checking payment {payment.id} status: {e}")
                        payment.status = PaymentStatus.FAILED
                else:
                    payment.status = PaymentStatus.FAILED
            
            if old_payments:
                await session.commit()
                logger.info(f"Cleaned up {len(old_payments)} pending payments")
            
    except Exception as e:
        logger.error(f"Error in cleanup_pending_payments: {e}")
        raise
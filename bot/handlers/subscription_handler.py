from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.models import User, Subscription, SubscriptionStatus, VPNConfig
from database.connection import async_session_maker
from sqlalchemy import select
from bot.keyboards.user import get_subscription_keyboard, get_back_button, get_payment_plans_keyboard
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("subscription"))
@router.callback_query(F.data == "my_subscription")
async def show_subscription(event: Message | CallbackQuery):
    """Show user subscription info"""
    
    # Get telegram_user_id from event
    if isinstance(event, Message):
        telegram_user_id = event.from_user.id
    elif isinstance(event, CallbackQuery):
        telegram_user_id = event.from_user.id
    else:
        return
    
    # Create database session
    session = async_session_maker()
    try:
        # Get user first
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            text = "❌ Пользователь не найден в системе"
            if isinstance(event, Message):
                await event.answer(text)
            else:
                await event.message.edit_text(text)
                await event.answer()
            return
        
        # Get active subscription
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            # Calculate days left
            days_left = (subscription.end_date - datetime.now()).days
            hours_left = ((subscription.end_date - datetime.now()).total_seconds() % 86400) // 3600
            
            # Get VPN config
            result = await session.execute(
                select(VPNConfig)
                .where(VPNConfig.user_id == user.id)
                .where(VPNConfig.is_active == True)
            )
            vpn_config = result.scalar_one_or_none()
            
            # Format subscription type based on status and plan
            if subscription.status == SubscriptionStatus.TRIAL:
                sub_type = "🎁 Пробный период"
            else:
                # Try to get plan name from the relationship or use generic name
                try:
                    if hasattr(subscription, 'plan') and subscription.plan:
                        sub_type = f"📅 {subscription.plan.name}"
                    else:
                        sub_type = "📅 Подписка"
                except:
                    sub_type = "📅 Подписка"
            
            # Format status
            if subscription.status == SubscriptionStatus.ACTIVE:
                status = "✅ Активна"
            elif subscription.status == SubscriptionStatus.TRIAL:
                status = "🎁 Триал"
            else:
                status = "❌ Неактивна"
            
            text = (
                f"💳 **Информация о подписке**\n\n"
                f"Тип: {sub_type}\n"
                f"Статус: {status}\n"
                f"Начало: {subscription.start_date.strftime('%d.%m.%Y')}\n"
                f"Окончание: {subscription.end_date.strftime('%d.%m.%Y')}\n"
                f"Осталось: {days_left} дн. {hours_left} ч.\n"
                f"Автопродление: {'✅ Включено' if getattr(subscription, 'auto_renew', False) else '❌ Выключено'}\n"
            )
            
            if vpn_config:
                text += f"\nVPN статус: ✅ Настроен"
            else:
                text += f"\nVPN статус: ⚠️ Не настроен"
            
            has_active = True
        else:
            text = (
                f"💳 **Информация о подписке**\n\n"
                f"❌ У вас нет активной подписки\n\n"
                f"Оформите подписку для получения доступа к VPN"
            )
            has_active = False
        
        # Send or edit message
        if isinstance(event, Message):
            await event.answer(
                text,
                reply_markup=get_subscription_keyboard(has_active),
                parse_mode="Markdown"
            )
        else:
            await event.message.edit_text(
                text,
                reply_markup=get_subscription_keyboard(has_active),
                parse_mode="Markdown"
            )
            await event.answer()
    
    finally:
        await session.close()
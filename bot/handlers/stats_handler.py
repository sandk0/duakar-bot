from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.connection import async_session_maker
from database.models import User, Subscription, VPNConfig, Payment, PaymentStatus
from sqlalchemy import select, func
from datetime import datetime, timedelta
from bot.keyboards.user import get_back_button
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "stats")
@router.message(Command("stats"))
async def show_user_stats(event: Message | CallbackQuery):
    """Show user statistics"""
    
    # Get telegram_user_id
    if isinstance(event, Message):
        telegram_user_id = event.from_user.id
        answer_func = event.answer
    else:
        telegram_user_id = event.from_user.id
        answer_func = event.message.edit_text
        await event.answer()
    
    session = async_session_maker()
    try:
        # Get user
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await answer_func(
                "❌ Пользователь не найден в системе\n"
                "Используйте /start для регистрации"
            )
            return
        
        # Get user's total payments
        payments_result = await session.execute(
            select(func.count(Payment.id), func.sum(Payment.amount))
            .where(Payment.user_id == user.id)
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_payments, total_spent = payments_result.one()
        total_spent = total_spent or 0
        
        # Get active subscription info
        active_sub_result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.is_active == True)
            .order_by(Subscription.created_at.desc())
        )
        active_sub = active_sub_result.scalar_one_or_none()
        
        # Get total subscription days
        subs_result = await session.execute(
            select(func.sum(Subscription.end_date - Subscription.start_date))
            .where(Subscription.user_id == user.id)
        )
        total_days_raw = subs_result.scalar()
        total_days = total_days_raw.days if total_days_raw else 0
        
        # Get VPN config if exists
        vpn_result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = vpn_result.scalar_one_or_none()
        
        # Get referral stats
        referrals_result = await session.execute(
            select(func.count(User.id))
            .where(User.referrer_id == user.id)
        )
        referral_count = referrals_result.scalar() or 0
        
        # Build statistics message
        text = (
            f"📊 **Ваша статистика**\n\n"
            f"👤 **Профиль:**\n"
            f"├ ID: `{user.telegram_id}`\n"
            f"├ Имя: {user.first_name or 'Не указано'}\n"
            f"├ Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}\n"
            f"└ Реферальный код: `ref_{user.telegram_id}`\n\n"
        )
        
        # Subscription info
        if active_sub:
            days_left = (active_sub.end_date - datetime.now()).days
            text += (
                f"💳 **Подписка:**\n"
                f"├ Статус: ✅ Активна\n"
                f"├ Окончание: {active_sub.end_date.strftime('%d.%m.%Y')}\n"
                f"├ Осталось дней: {days_left}\n"
                f"└ Всего дней подписки: {total_days}\n\n"
            )
        else:
            text += (
                f"💳 **Подписка:**\n"
                f"├ Статус: ❌ Неактивна\n"
                f"└ Всего дней подписки: {total_days}\n\n"
            )
        
        # VPN info
        if vpn_config:
            text += (
                f"🔐 **VPN:**\n"
                f"├ Конфигурация: ✅ Создана\n"
                f"├ Протокол: {vpn_config.protocol or 'VLESS'}\n"
                f"├ Использовано трафика: {format_bytes(vpn_config.traffic_used or 0)}\n"
                f"└ Последнее подключение: {vpn_config.last_connected_at.strftime('%d.%m.%Y %H:%M') if vpn_config.last_connected_at else 'Никогда'}\n\n"
            )
        else:
            text += (
                f"🔐 **VPN:**\n"
                f"└ Конфигурация: ❌ Не создана\n\n"
            )
        
        # Payment info
        text += (
            f"💰 **Платежи:**\n"
            f"├ Всего платежей: {total_payments}\n"
            f"└ Общая сумма: {total_spent:.2f} ₽\n\n"
        )
        
        # Referral info
        text += (
            f"👥 **Рефералы:**\n"
            f"├ Приглашено: {referral_count} чел.\n"
            f"└ Бонусные дни: {user.bonus_days or 0}\n"
        )
        
        await answer_func(
            text,
            parse_mode="Markdown",
            reply_markup=get_back_button()
        )
        
    except Exception as e:
        logger.error(f"Error showing user stats: {e}")
        await answer_func(
            "❌ Произошла ошибка при получении статистики\n"
            "Попробуйте позже или обратитесь в поддержку"
        )
    finally:
        await session.close()


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"
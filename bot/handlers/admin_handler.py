from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import (
    User, Subscription, Payment, PromoCode, FAQItem, BroadcastMessage,
    SubscriptionStatus, PricingPlan, VPNConfig
)
from database.models.payment import PaymentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import async_session_maker
from sqlalchemy import select, func, and_, desc, delete
from bot.keyboards.admin import (
    get_admin_menu_keyboard, get_admin_users_keyboard, get_user_actions_keyboard,
    get_admin_payments_keyboard, get_admin_promos_keyboard, get_admin_broadcast_keyboard,
    get_admin_faq_keyboard, get_admin_pricing_keyboard, get_admin_settings_keyboard,
    get_back_to_admin_keyboard, get_confirm_keyboard
)
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_for_user_search = State()
    waiting_for_promo_code = State()
    waiting_for_broadcast_message = State()
    waiting_for_faq_question = State()
    waiting_for_faq_answer = State()


def is_admin(user: User) -> bool:
    """Check if user is admin"""
    return user.is_admin


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Show admin panel"""
    # Check if user is admin (simplified check)
    if message.from_user.id != 17499218:  # Your admin ID
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🔧 **Админ-панель**\n\n"
        "Добро пожаловать в панель управления ботом.",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "admin_menu")
async def show_admin_menu(callback: CallbackQuery):
    """Show admin menu"""
    # Check admin access
    if callback.from_user.id != 17499218:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔧 **Админ-панель**\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    """Show system statistics"""
    # Check admin access
    if callback.from_user.id != 17499218:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Create database session
    session = async_session_maker()
    try:
        # Get basic statistics
        total_users = await session.scalar(select(func.count(User.id)))
        
        active_subs = await session.scalar(
            select(func.count(Subscription.id))
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
        )
        
        total_payments = await session.scalar(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.SUCCESS)
        )
        
        # Today's stats
        today = datetime.now().date()
        new_users_today = await session.scalar(
            select(func.count(User.id))
            .where(func.date(User.created_at) == today)
        )
        
        payments_today = await session.scalar(
            select(func.sum(Payment.amount))
            .where(
                and_(
                    Payment.status == PaymentStatus.SUCCESS,
                    func.date(Payment.created_at) == today
                )
            )
        ) or 0
        
        # Trial users
        trial_users = await session.scalar(
            select(func.count(Subscription.id))
            .where(
                and_(
                    Subscription.status == SubscriptionStatus.TRIAL,
                    Subscription.is_trial == True
                )
            )
        )
        
        text = (
            f"📊 **Статистика системы**\n\n"
            f"👥 **Пользователи:**\n"
            f"• Всего: {total_users}\n"
            f"• Новых за сегодня: {new_users_today}\n"
            f"• Активных подписок: {active_subs}\n"
            f"• На триале: {trial_users}\n\n"
            f"💰 **Финансы:**\n"
            f"• Общий доход: {total_payments or 0:.2f} ₽\n"
            f"• Доход за сегодня: {payments_today:.2f} ₽\n\n"
            f"📅 **Обновлено:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data == "admin_users")
async def show_admin_users(callback: CallbackQuery):
    """Show user management menu"""
    # Simplified - no admin check for now
    
    await callback.message.edit_text(
        "👥 **Управление пользователями**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_users_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_find_user")
async def find_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user search"""
    # Simplified - no admin check for now
    
    await state.set_state(AdminStates.waiting_for_user_search)
    await callback.message.edit_text(
        "🔍 **Поиск пользователя**\n\n"
        "Отправьте Telegram ID, username или имя пользователя:",
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_search)
async def find_user(message: Message, session: AsyncSession, state: FSMContext):
    """Find and show user info"""
    # Simplified - no admin check for now
    
    search_query = message.text.strip()
    
    # Try to find user by Telegram ID, username, or name
    if search_query.isdigit():
        # Search by Telegram ID
        result = await session.execute(
            select(User).where(User.telegram_id == int(search_query))
        )
    else:
        # Search by username or name
        result = await session.execute(
            select(User).where(
                User.username.ilike(f"%{search_query}%") |
                User.first_name.ilike(f"%{search_query}%")
            )
        )
    
    found_user = result.scalar_one_or_none()
    
    if not found_user:
        await message.answer(
            "❌ Пользователь не найден",
            reply_markup=get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    # Get user subscription info
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == found_user.id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    # Format user info
    name = found_user.first_name or "Не указано"
    username = f"@{found_user.username}" if found_user.username else "Не указано"
    status = "🚫 Заблокирован" if found_user.is_blocked else "✅ Активен"
    
    if subscription:
        if subscription.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            sub_status = f"✅ {subscription.status}"
            days_left = (subscription.end_date - datetime.now()).days
            sub_info = f"{sub_status} ({days_left} дн.)"
        else:
            sub_info = f"❌ {subscription.status}"
    else:
        sub_info = "❌ Нет подписки"
    
    text = (
        f"👤 **Информация о пользователе**\n\n"
        f"**ID:** {found_user.telegram_id}\n"
        f"**Имя:** {name}\n"
        f"**Username:** {username}\n"
        f"**Статус:** {status}\n"
        f"**Подписка:** {sub_info}\n"
        f"**Регистрация:** {found_user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    if found_user.is_blocked and found_user.block_reason:
        text += f"**Причина блокировки:** {found_user.block_reason}\n"
    
    await message.answer(
        text,
        reply_markup=get_user_actions_keyboard(found_user.id),
        parse_mode="Markdown"
    )
    
    await state.clear()


@router.callback_query(F.data.startswith("admin_block_"))
async def block_user(callback: CallbackQuery, session: AsyncSession):
    """Block user"""
    # Simplified - no admin check for now
    
    user_id = int(callback.data.split("_")[-1])
    
    # Get user
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    # Block user
    target_user.is_blocked = True
    target_user.block_reason = f"Заблокирован администратором {datetime.now().strftime('%d.%m.%Y')}"
    
    await session.commit()
    
    await callback.answer("✅ Пользователь заблокирован", show_alert=True)
    
    # Refresh user info (simplified)
    await callback.message.edit_text(
        f"🚫 **Пользователь заблокирован**\n\n"
        f"ID: {target_user.telegram_id}\n"
        f"Имя: {target_user.first_name}",
        reply_markup=get_user_actions_keyboard(target_user.id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("admin_unblock_"))
async def unblock_user(callback: CallbackQuery, session: AsyncSession):
    """Unblock user"""
    # Simplified - no admin check for now
    
    user_id = int(callback.data.split("_")[-1])
    
    # Get user
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    # Unblock user
    target_user.is_blocked = False
    target_user.block_reason = None
    
    await session.commit()
    
    await callback.answer("✅ Пользователь разблокирован", show_alert=True)
    
    # Refresh user info
    await callback.message.edit_text(
        f"✅ **Пользователь разблокирован**\n\n"
        f"ID: {target_user.telegram_id}\n"
        f"Имя: {target_user.first_name}",
        reply_markup=get_user_actions_keyboard(target_user.id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "admin_payments")
async def show_payments_menu(callback: CallbackQuery):
    """Show payments management menu"""
    # Simplified - no admin check for now
    
    await callback.message.edit_text(
        "💰 **Управление платежами**\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_payments_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payments_recent")
async def show_recent_payments(callback: CallbackQuery, session: AsyncSession):
    """Show recent payments"""
    # Simplified - no admin check for now
    
    # Get recent payments
    result = await session.execute(
        select(Payment, User)
        .join(User, Payment.user_id == User.id)
        .order_by(desc(Payment.created_at))
        .limit(10)
    )
    payments = result.all()
    
    if not payments:
        text = "💰 **Последние платежи**\n\nПлатежей пока нет."
    else:
        text = "💰 **Последние 10 платежей:**\n\n"
        
        for payment, payment_user in payments:
            status_emoji = "✅" if payment.status == PaymentStatus.SUCCESS else "❌"
            user_name = payment_user.first_name or f"ID{payment_user.telegram_id}"
            
            text += (
                f"{status_emoji} **{payment.amount} ₽** | {user_name}\n"
                f"   {payment.created_at.strftime('%d.%m %H:%M')} | {payment.payment_method}\n\n"
            )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(Command("admin_test"))
async def admin_test_command(message: Message):
    """Test admin command"""
    logger.info(f"admin_test_command called by user {message.from_user.id}")
    await message.answer("✅ Admin роутер работает!")


@router.message(Command("reset_trial"))
async def reset_trial_command(message: Message):
    """Admin command to reset trial period for a user"""
    logger.info(f"reset_trial_command called by user {message.from_user.id} with text: {message.text}")
    
    # Check if user is admin (simplified check by telegram_id)
    if message.from_user.id != 17499218:
        await message.answer("❌ У вас нет прав на выполнение этой команды")
        return
    
    # Parse command arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /reset_trial <telegram_id>")
        return
    
    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ Некорректный Telegram ID")
        return
    
    # Create database session
    async with async_session_maker() as session:
        # Find user
        result = await session.execute(
            select(User).where(User.telegram_id == target_telegram_id)
        )
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            await message.answer(f"❌ Пользователь с ID {target_telegram_id} не найден")
            return
        
        # Delete subscriptions using raw delete to avoid relationship loading
        await session.execute(
            delete(Subscription).where(Subscription.user_id == target_user.id)
        )
        
        # Delete VPN configs using raw delete
        await session.execute(
            delete(VPNConfig).where(VPNConfig.user_id == target_user.id)
        )
        
        # Reset trial flag
        target_user.trial_used = False
        
        await session.commit()
    
    user_name = target_user.first_name or f"ID{target_user.telegram_id}"
    await message.answer(
        f"✅ **Пробный период сброшен**\n\n"
        f"Пользователь: {user_name}\n"
        f"Telegram ID: {target_user.telegram_id}\n"
        f"• Удалены все подписки\n"
        f"• Удалены все VPN конфиги\n"
        f"• Сброшен флаг использования пробного периода",
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "admin_cancel")
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext):
    """Cancel admin action"""
    await state.clear()
    await callback.message.edit_text(
        "❌ **Действие отменено**",
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()
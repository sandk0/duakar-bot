from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.models import User, ReferralStat, Subscription, SubscriptionStatus
from database.connection import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.keyboards.user import get_back_button
from bot.config import settings
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("referral"))
@router.callback_query(F.data == "referral")
async def show_referral_info(event: Message | CallbackQuery):
    """Show referral program information"""
    
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
        
        # Get or create referral stats
        result = await session.execute(
            select(ReferralStat).where(ReferralStat.user_id == user.id)
        )
        referral_stat = result.scalar_one_or_none()
        
        if not referral_stat:
            referral_stat = ReferralStat(user_id=user.id)
            session.add(referral_stat)
            await session.commit()
            await session.refresh(referral_stat)
        
        # Get referrals count and their activity
        result = await session.execute(
            select(User).where(User.referred_by == user.id)
        )
        referrals = result.scalars().all()
        
        # Count active referrals (those who have active subscriptions)
        active_referrals = 0
        for referral in referrals:
            result = await session.execute(
                select(Subscription)
                .where(Subscription.user_id == referral.id)
                .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
            )
            if result.scalar_one_or_none():
                active_referrals += 1
        
        # Generate referral link
        bot_username = settings.bot_username.lstrip('@')
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.telegram_id}"
        
        # Calculate available bonus days
        available_bonus = referral_stat.bonus_days_earned - referral_stat.bonus_days_used
        
        text = (
            f"👥 **Реферальная программа**\n\n"
            f"🎁 **Ваши бонусы:**\n"
            f"• Приглашено друзей: **{len(referrals)}**\n"
            f"• Активных рефералов: **{active_referrals}**\n"
            f"• Заработано дней: **{referral_stat.bonus_days_earned}**\n"
            f"• Использовано дней: **{referral_stat.bonus_days_used}**\n"
            f"• Доступно к использованию: **{available_bonus}** дней\n\n"
            
            f"📋 **Условия программы:**\n"
            f"• Вы получаете **{settings.referral_bonus_days} дней** за каждого друга\n"
            f"• Ваш друг получает **{settings.referral_friend_bonus_days} дней** при первой оплате\n"
            f"• Бонусы начисляются после первой оплаты реферала\n"
            f"• Бонусные дни можно использовать для продления подписки\n\n"
            
            f"🔗 **Ваша реферальная ссылка:**\n"
            f"`{referral_link}`\n\n"
            
            f"📤 **Как пригласить друзей:**\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. Отправьте другу в любой мессенджер\n"
            f"3. Друг регистрируется по вашей ссылке\n"
            f"4. После его первой оплаты вы оба получите бонусы!"
        )
        
        if isinstance(event, Message):
            await event.answer(
                text,
                reply_markup=get_back_button("main_menu"),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await event.message.edit_text(
                text,
                reply_markup=get_back_button("main_menu"),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            await event.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data == "use_bonus_days")
async def use_bonus_days(callback: CallbackQuery):
    """Use bonus days to extend subscription"""
    telegram_user_id = callback.from_user.id
    
    # Create database session
    session = async_session_maker()
    try:
        # Get user first
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Get referral stats
        result = await session.execute(
            select(ReferralStat).where(ReferralStat.user_id == user.id)
        )
        referral_stat = result.scalar_one_or_none()
        
        if not referral_stat:
            await callback.answer("У вас нет бонусных дней", show_alert=True)
            return
        
        available_bonus = referral_stat.bonus_days_earned - referral_stat.bonus_days_used
        
        if available_bonus <= 0:
            await callback.answer("У вас нет доступных бонусных дней", show_alert=True)
            return
        
        # Get current active subscription
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            await callback.answer("У вас нет активной подписки для продления", show_alert=True)
            return
        
        # Extend subscription with bonus days
        from datetime import datetime, timedelta
        
        subscription.end_date = subscription.end_date + timedelta(days=available_bonus)
        referral_stat.bonus_days_used += available_bonus
        
        await session.commit()
        
        await callback.answer(
            f"✅ Подписка продлена на {available_bonus} дней!",
            show_alert=True
        )
        
        # Refresh referral info (reload the page)
        await show_referral_info(callback)
    
    finally:
        await session.close()


@router.callback_query(F.data == "referral_history")
async def show_referral_history(callback: CallbackQuery):
    """Show detailed referral history"""
    telegram_user_id = callback.from_user.id
    
    # Create database session
    session = async_session_maker()
    try:
    
        # Get user first
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "❌ Пользователь не найден",
                reply_markup=get_back_button("referral")
            )
            await callback.answer()
            return
        
        # Get all referrals with their subscription status
        result = await session.execute(
            select(User).where(User.referred_by == user.id).order_by(User.created_at.desc())
        )
        referrals = result.scalars().all()
        
        if not referrals:
            text = "👥 **История рефералов**\n\nУ вас пока нет приглашенных друзей."
        else:
            text = f"👥 **История рефералов** ({len(referrals)}):\n\n"
            
            for i, referral in enumerate(referrals[:20], 1):  # Show max 20
                # Check if referral has active subscription
                result = await session.execute(
                    select(Subscription)
                    .where(Subscription.user_id == referral.id)
                    .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
                )
                active_sub = result.scalar_one_or_none()
                
                # Get total payments count
                result = await session.execute(
                    select(func.count(Subscription.id))
                    .where(Subscription.user_id == referral.id)
                    .where(Subscription.status != SubscriptionStatus.PENDING)
                )
                payments_count = result.scalar() or 0
                
                status = "✅ Активен" if active_sub else "❌ Неактивен"
                name = referral.first_name or "Пользователь"
                
                text += (
                    f"{i}. **{name}** {status}\n"
                    f"   Регистрация: {referral.created_at.strftime('%d.%m.%Y')}\n"
                    f"   Оплат: {payments_count}\n\n"
                )
            
            if len(referrals) > 20:
                text += f"... и еще {len(referrals) - 20} рефералов"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("referral"),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        await session.close()


async def process_referral_bonus(referrer_id: int, referral_id: int, session: AsyncSession):
    """Process referral bonus after successful payment"""
    try:
        # Get referrer's stats
        result = await session.execute(
            select(ReferralStat).where(ReferralStat.user_id == referrer_id)
        )
        referral_stat = result.scalar_one_or_none()
        
        if not referral_stat:
            referral_stat = ReferralStat(user_id=referrer_id)
            session.add(referral_stat)
        
        # Check if bonus already given for this referral
        result = await session.execute(
            select(func.count())
            .where(User.id == referral_id)
            .where(User.referred_by == referrer_id)
        )
        
        if result.scalar() > 0:  # Referral relationship exists
            # Add bonus days
            referral_stat.bonus_days_earned += settings.referral_bonus_days
            await session.commit()
            
            logger.info(f"Referral bonus {settings.referral_bonus_days} days given to user {referrer_id}")
            return True
    
    except Exception as e:
        logger.error(f"Error processing referral bonus: {e}")
        return False
    
    return False
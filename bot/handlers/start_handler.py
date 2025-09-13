from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot.keyboards.user import get_main_menu_keyboard, get_start_keyboard
from database.models import User, Subscription, ReferralStat, SubscriptionStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from services.marzban import marzban_client, generate_unique_username
from bot.config import settings
import re
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    telegram_user_id = message.from_user.id
    
    welcome_text = (
        f"👋 Добро пожаловать в VPN Bot, {message.from_user.first_name}!\n\n"
        f"🤖 Бот работает!\n"
        f"Ваш Telegram ID: {telegram_user_id}\n\n"
        f"Используйте /menu для доступа к основным функциям бота."
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())


@router.message(Command("menu"))
async def menu_command(message: Message):
    """Handle /menu command"""
    logger.info(f"Menu command received from user {message.from_user.id}")
    await message.answer(
        "📱 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    help_text = (
        "❓ **Помощь**\n\n"
        "**Основные команды:**\n"
        "• /start - Начать работу с ботом\n"
        "• /menu - Главное меню\n"
        "• /subscription - Управление подпиской\n"
        "• /config - Получить VPN конфигурацию\n"
        "• /referral - Реферальная программа\n"
        "• /support - Техническая поддержка\n"
        "• /help - Эта справка\n\n"
        "**Для получения VPN:**\n"
        "1. Оформите подписку (/subscription)\n"
        "2. Получите конфигурацию (/config)\n"
        "3. Настройте VPN на устройстве\n\n"
        "По всем вопросам: /support"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Handle /cancel command"""
    await state.clear()
    await message.answer(
        "❌ **Действие отменено**\n\n"
        "Используйте /menu для возврата к главному меню.",
        parse_mode="Markdown"
    )


async def process_referral(user: User, referral_code: str, session: AsyncSession):
    """Process referral code"""
    try:
        # Extract referrer ID from code
        match = re.match(r"ref_(\d+)", referral_code)
        if not match:
            return
        
        referrer_id = int(match.group(1))
        
        # Get referrer
        result = await session.execute(
            select(User).where(User.telegram_id == referrer_id)
        )
        referrer = result.scalar_one_or_none()
        
        if not referrer or referrer.id == user.id:
            return
        
        # Set referrer
        user.referrer_id = referrer.id
        
        # Update referral stats
        result = await session.execute(
            select(ReferralStat).where(ReferralStat.user_id == referrer.id)
        )
        referral_stat = result.scalar_one_or_none()
        
        if not referral_stat:
            referral_stat = ReferralStat(user_id=referrer.id)
            session.add(referral_stat)
        
        referral_stat.referral_count += 1
        
        await session.commit()
        logger.info(f"User {user.telegram_id} referred by {referrer.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error processing referral: {e}")


async def create_trial_subscription(user: User, session: AsyncSession):
    """Create trial subscription for new user"""
    try:
        # Create subscription in database
        subscription = Subscription(
            user_id=user.id,
            plan_type="trial",
            status=SubscriptionStatus.TRIAL,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=settings.trial_days),
            is_trial=True,
            auto_renewal=False
        )
        session.add(subscription)
        
        # Create VPN config in Marzban
        async with marzban_client as client:
            marzban_username = generate_unique_username(user.telegram_id)
            marzban_user = await client.create_user(
                username=marzban_username,
                expire_days=settings.trial_days,
                note=f"Trial user: {user.telegram_id}"
            )
            
            # Save VPN config
            from database.models import VPNConfig
            vpn_config = VPNConfig(
                user_id=user.id,
                marzban_user_id=marzban_username,
                config_url=marzban_user.links[0] if marzban_user.links else None,
                is_active=True
            )
            session.add(vpn_config)
        
        await session.commit()
        logger.info(f"Created trial subscription for user {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error creating trial subscription: {e}")
        await session.rollback()


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Return to main menu"""
    await callback.message.edit_text(
        "📱 Главное меню\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.message(Command("test_routing"))
async def test_routing_command(message: Message):
    """Test command to check routing"""
    logger.info(f"test_routing_command called by user {message.from_user.id}")
    await message.answer("✅ Роутинг работает в start_handler!")


@router.message(Command("reset_trial_simple"))
async def reset_trial_simple_command(message: Message):
    """Simple admin command for trial reset in start handler"""
    if message.from_user.id != 17499218:
        await message.answer("❌ У вас нет прав на выполнение этой команды")
        return
    
    logger.info(f"reset_trial_simple_command called by user {message.from_user.id} with text: {message.text}")
    
    # Parse command arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /reset_trial_simple <telegram_id>")
        return
    
    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ Некорректный Telegram ID")
        return
    
    # Use simple SQL reset
    await message.answer(f"🔄 Сбрасываю пробный период для пользователя {target_telegram_id}...")
    
    # Use the existing database function
    from database.connection import async_session_maker
    from database.models import User, Subscription, VPNConfig
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        try:
            # Find user
            result = await session.execute(
                select(User).where(User.telegram_id == target_telegram_id)
            )
            target_user = result.scalar_one_or_none()
            
            if not target_user:
                await message.answer(f"❌ Пользователь с ID {target_telegram_id} не найден")
                return
            
            # Delete subscriptions and configs
            result = await session.execute(select(Subscription).where(Subscription.user_id == target_user.id))
            for sub in result.scalars().all():
                await session.delete(sub)
            
            result = await session.execute(select(VPNConfig).where(VPNConfig.user_id == target_user.id))  
            for config in result.scalars().all():
                await session.delete(config)
            
            # Reset trial flag
            target_user.trial_used = False
            await session.commit()
            
            await message.answer(f"✅ Пробный период сброшен для пользователя {target_user.first_name or target_user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error in reset_trial_simple: {e}")
            await message.answer(f"❌ Ошибка: {e}")



from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.connection import async_session_maker
from database.models import User, Subscription, VPNConfig
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)
router = Router()


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
        try:
            # Find user
            result = await session.execute(
                select(User).where(User.telegram_id == target_telegram_id)
            )
            target_user = result.scalar_one_or_none()
            
            if not target_user:
                await message.answer(f"❌ Пользователь с ID {target_telegram_id} не найден")
                return
            
            # Delete subscriptions
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == target_user.id)
            )
            subscriptions = result.scalars().all()
            for subscription in subscriptions:
                await session.delete(subscription)
            
            # Delete VPN configs
            result = await session.execute(
                select(VPNConfig).where(VPNConfig.user_id == target_user.id)
            )
            vpn_configs = result.scalars().all()
            for config in vpn_configs:
                await session.delete(config)
            
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
            
        except Exception as e:
            logger.error(f"Error in reset_trial_command: {e}")
            await message.answer(f"❌ Ошибка при сбросе: {str(e)}")
            await session.rollback()
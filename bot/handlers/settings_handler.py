from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.connection import async_session_maker
from database.models import User
from sqlalchemy import select, update
from bot.keyboards.user import get_back_button
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    """States for settings management"""
    changing_language = State()


def get_settings_keyboard(user) -> InlineKeyboardMarkup:
    """Get settings keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Language setting
    current_lang = getattr(user, 'language', 'ru') or 'ru'
    lang_text = "🇷🇺 Русский" if current_lang == 'ru' else "🇬🇧 English"
    builder.row(
        InlineKeyboardButton(text=f"🌐 Язык: {lang_text}", callback_data="change_language")
    )
    
    # Notification settings
    notifications = getattr(user, 'notifications_enabled', True)
    notif_text = "✅ Включены" if notifications else "❌ Выключены"
    builder.row(
        InlineKeyboardButton(text=f"🔔 Уведомления: {notif_text}", callback_data="toggle_notifications")
    )
    
    # Auto-renewal setting
    auto_renew = getattr(user, 'auto_renew', False)
    renew_text = "✅ Включено" if auto_renew else "❌ Выключено"
    builder.row(
        InlineKeyboardButton(text=f"🔄 Автопродление: {renew_text}", callback_data="toggle_autorenew")
    )
    
    # Delete account
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data="delete_account")
    )
    
    # Back button
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


@router.callback_query(F.data == "settings")
@router.message(Command("settings"))
async def show_settings(event: Message | CallbackQuery):
    """Show user settings"""
    
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
        
        text = (
            "⚙️ **Настройки**\n\n"
            "Здесь вы можете настроить параметры вашего аккаунта"
        )
        
        await answer_func(
            text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user)
        )
        
    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await answer_func(
            "❌ Произошла ошибка при загрузке настроек"
        )
    finally:
        await session.close()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Toggle notification settings"""
    telegram_user_id = callback.from_user.id
    
    session = async_session_maker()
    try:
        # Get user
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Toggle notifications
        current_state = getattr(user, 'notifications_enabled', True)
        new_state = not current_state
        
        # Update user (assuming notifications_enabled field exists)
        # If field doesn't exist, this will need to be added to the model
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(notifications_enabled=new_state)
        )
        await session.commit()
        
        # Refresh user object
        await session.refresh(user)
        
        # Update message
        text = (
            "⚙️ **Настройки**\n\n"
            "Здесь вы можете настроить параметры вашего аккаунта"
        )
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user)
        )
        
        status = "включены" if new_state else "выключены"
        await callback.answer(f"✅ Уведомления {status}")
        
    except Exception as e:
        logger.error(f"Error toggling notifications: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        await session.close()


@router.callback_query(F.data == "toggle_autorenew")
async def toggle_autorenew(callback: CallbackQuery):
    """Toggle auto-renewal settings"""
    telegram_user_id = callback.from_user.id
    
    session = async_session_maker()
    try:
        # Get user
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Toggle auto-renewal
        current_state = getattr(user, 'auto_renew', False)
        new_state = not current_state
        
        # Update user
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(auto_renew=new_state)
        )
        await session.commit()
        
        # Refresh user object
        await session.refresh(user)
        
        # Update message
        text = (
            "⚙️ **Настройки**\n\n"
            "Здесь вы можете настроить параметры вашего аккаунта"
        )
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user)
        )
        
        status = "включено" if new_state else "выключено"
        await callback.answer(f"✅ Автопродление {status}")
        
    except Exception as e:
        logger.error(f"Error toggling auto-renewal: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        await session.close()


@router.callback_query(F.data == "change_language")
async def change_language(callback: CallbackQuery):
    """Change interface language"""
    # For now, just show a message that this feature is coming soon
    await callback.answer(
        "🚧 Смена языка будет доступна в следующей версии",
        show_alert=True
    )


@router.callback_query(F.data == "delete_account")
async def delete_account_confirm(callback: CallbackQuery):
    """Confirm account deletion"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚠️ Да, удалить", callback_data="confirm_delete_account"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="settings")
    )
    
    await callback.message.edit_text(
        "⚠️ **Внимание!**\n\n"
        "Вы уверены, что хотите удалить аккаунт?\n"
        "Это действие необратимо!\n\n"
        "• Все ваши данные будут удалены\n"
        "• Активная подписка будет отменена\n"
        "• VPN конфигурация будет деактивирована",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_account")
async def confirm_delete_account(callback: CallbackQuery):
    """Actually delete the account"""
    # For safety, we won't actually delete the account
    # In production, this would require additional confirmation
    await callback.message.edit_text(
        "🔒 **Защита от случайного удаления**\n\n"
        "Для удаления аккаунта обратитесь в поддержку /support\n"
        "с указанием причины удаления.",
        parse_mode="Markdown",
        reply_markup=get_back_button()
    )
    await callback.answer("Обратитесь в поддержку для удаления аккаунта", show_alert=True)
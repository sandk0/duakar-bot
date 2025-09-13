from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from database.models import User, Subscription, SubscriptionStatus, VPNConfig
from database.connection import async_session_maker
from sqlalchemy import select
from bot.keyboards.user import (
    get_config_keyboard, get_platform_keyboard, get_back_button
)
from services.marzban import marzban_client, generate_config_qr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()

# Fixed handlers without kwargs dependency

@router.message(Command("config"))
@router.callback_query(F.data == "get_config")
async def get_config(event: Message | CallbackQuery):
    """Get VPN configuration"""
    logger.info(f"get_config handler called! Event type: {type(event)}")
    
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
        
        # Check if user has active subscription
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            text = (
                "❌ **Нет активной подписки**\n\n"
                "Для получения VPN конфигурации необходимо оформить подписку."
            )
            if isinstance(event, Message):
                await event.answer(text, parse_mode="Markdown")
            else:
                await event.message.edit_text(text, parse_mode="Markdown")
                await event.answer()
            return
        
        # Get VPN config
        result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = result.scalar_one_or_none()
        
        if not vpn_config or not vpn_config.config_data:
            text = (
                "⚠️ **VPN конфигурация не найдена**\n\n"
                "Попробуйте обновить конфигурацию или обратитесь в поддержку."
            )
            if isinstance(event, Message):
                await event.answer(text, parse_mode="Markdown")
            else:
                await event.message.edit_text(text, parse_mode="Markdown")
                await event.answer()
            return
        
        # Update last used
        vpn_config.updated_at = datetime.now()
        await session.commit()
        
        # Calculate subscription info
        days_left = (subscription.end_date - datetime.now()).days
        
        text = (
            f"🔑 **Ваша VPN конфигурация**\n\n"
            f"Статус: ✅ Активна\n"
            f"Осталось дней: {days_left}\n"
            f"Протокол: VLESS\n\n"
            f"⚠️ **Важно:**\n"
            f"• Конфигурация работает только на одном устройстве\n"
            f"• При подключении нового устройства предыдущее отключается\n"
            f"• Не передавайте конфигурацию третьим лицам\n\n"
            f"📱 **Выберите VPN-клиент для быстрой настройки:**"
        )
        
        if isinstance(event, Message):
            await event.answer(
                text,
                reply_markup=get_config_keyboard(vpn_config.config_data),
                parse_mode="Markdown"
            )
        else:
            await event.message.edit_text(
                text,
                reply_markup=get_config_keyboard(vpn_config.config_data),
                parse_mode="Markdown"
            )
            await event.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data == "show_qr")
async def show_qr_code(callback: CallbackQuery):
    """Show QR code for VPN config"""
    logger.info(f"show_qr_code handler called by user {callback.from_user.id}")
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
        
        # Get VPN config
        result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = result.scalar_one_or_none()
        
        if not vpn_config or not vpn_config.config_data:
            await callback.answer("VPN конфигурация не найдена", show_alert=True)
            return
        
        try:
            # Generate QR code
            qr_image = generate_config_qr(vpn_config.config_data)
            
            # Create keyboard with quick action buttons
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            
            builder = InlineKeyboardBuilder()
            
            # Add button to copy config (callback instead of URL)
            builder.row(
                InlineKeyboardButton(
                    text="📋 Скопировать конфигурацию", 
                    callback_data="copy_link"
                )
            )
            
            
            # Add back button
            builder.row(
                InlineKeyboardButton(text="◀️ Назад", callback_data="get_config")
            )
            
            # Send QR code as photo with improved caption
            caption = (
                "<b>📱 QR-код для быстрого подключения</b>\n\n"
                "<b>Как использовать:</b>\n"
                "1. Откройте VPN-клиент на телефоне\n"
                "2. Выберите «Добавить из QR-кода»\n"
                "3. Отсканируйте код с экрана\n\n"
                "💡 <i>Или нажмите кнопку ниже для автоматической настройки</i>"
            )
            
            await callback.message.answer_photo(
                BufferedInputFile(qr_image.getvalue(), filename="vpn_config_qr.png"),
                caption=caption,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            
            await callback.answer("✅ QR-код отправлен")
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            await callback.answer("Ошибка генерации QR-кода", show_alert=True)
    
    finally:
        await session.close()


@router.callback_query(F.data == "copy_link")
async def copy_config_link(callback: CallbackQuery):
    """Send config link for copying"""
    logger.info(f"copy_config_link handler called by user {callback.from_user.id}")
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
        
        # Get VPN config
        result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = result.scalar_one_or_none()
        
        if not vpn_config or not vpn_config.config_data:
            await callback.answer("VPN конфигурация не найдена", show_alert=True)
            return
        
        # Create simple back button
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="get_config")
        )
        
        # Send config with simple formatting for copying
        config_message = (
            "<b>🔗 Ваша VPN конфигурация</b>\n\n"
            "<b>Инструкция:</b>\n"
            "1️⃣ Нажмите и удерживайте ссылку ниже\n"
            "2️⃣ Выберите \"Копировать\"\n"
            "3️⃣ Вставьте в VPN-клиент\n\n"
            "📋 <b>VLESS конфигурация:</b>\n\n"
            f"<code>{vpn_config.config_data}</code>\n\n"
            "💡 <i>Поддерживаемые приложения: v2rayNG, Shadowrocket, FoXray, V2Box, NekoBox и другие</i>"
        )
        
        await callback.message.answer(
            config_message,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        await callback.answer("✅ Ссылка отправлена! Нажмите для копирования", show_alert=False)
    
    finally:
        await session.close()


@router.callback_query(F.data == "install_guide")
async def installation_guide(callback: CallbackQuery, **kwargs):
    """Show installation guide"""
    await callback.message.edit_text(
        "📖 **Выберите вашу платформу:**\n\n"
        "Мы подготовили подробные инструкции для каждой операционной системы",
        reply_markup=get_platform_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("guide_"))
async def show_platform_guide(callback: CallbackQuery, **kwargs):
    """Show installation guide for specific platform"""
    platform = callback.data.replace("guide_", "")
    
    guides = {
        "ios": {
            "title": "📱 Настройка на iOS",
            "content": (
                "**1. Скачайте приложение:**\n"
                "• Shadowrocket (платное)\n"
                "• OneClick (бесплатное)\n\n"
                "**2. Добавьте конфигурацию:**\n"
                "• Скопируйте VLESS ссылку из бота\n"
                "• Откройте приложение\n"
                "• Нажмите '+' → 'Add Server'\n"
                "• Вставьте ссылку\n\n"
                "**3. Подключение:**\n"
                "• Нажмите на переключатель\n"
                "• Разрешите создание VPN\n"
                "• Готово!"
            )
        },
        "android": {
            "title": "🤖 Настройка на Android",
            "content": (
                "**1. Скачайте приложение:**\n"
                "• v2rayNG (рекомендуется)\n"
                "• Clash for Android\n\n"
                "**2. Добавьте конфигурацию:**\n"
                "• Скопируйте VLESS ссылку\n"
                "• Откройте v2rayNG\n"
                "• Нажмите '+' в правом верхнем углу\n"
                "• Выберите 'Import from Clipboard'\n\n"
                "**3. Подключение:**\n"
                "• Выберите добавленный сервер\n"
                "• Нажмите кнопку подключения\n"
                "• Разрешите создание VPN"
            )
        },
        "windows": {
            "title": "💻 Настройка на Windows",
            "content": (
                "**1. Скачайте клиент:**\n"
                "• v2rayN (рекомендуется)\n"
                "• Clash for Windows\n\n"
                "**2. Установка v2rayN:**\n"
                "• Распакуйте архив\n"
                "• Запустите v2rayN.exe\n\n"
                "**3. Добавьте сервер:**\n"
                "• ПКМ по иконке в трее\n"
                "• Серверы → Добавить сервер VLESS\n"
                "• Вставьте ссылку из бота\n\n"
                "**4. Подключение:**\n"
                "• Выберите сервер в списке\n"
                "• ПКМ → Set as active server\n"
                "• HTTP прокси → Включить"
            )
        },
        "macos": {
            "title": "🍎 Настройка на macOS",
            "content": (
                "**1. Скачайте приложение:**\n"
                "• ClashX (рекомендуется)\n"
                "• V2RayX\n\n"
                "**2. Установка ClashX:**\n"
                "• Скачайте .dmg файл\n"
                "• Перетащите в Applications\n"
                "• Запустите приложение\n\n"
                "**3. Настройка:**\n"
                "• В меню ClashX выберите Config\n"
                "• Remote Config → Manage\n"
                "• Add → вставьте ссылку подписки\n\n"
                "**4. Подключение:**\n"
                "• Set as System Proxy\n"
                "• Выберите профиль\n"
                "• Проверьте подключение"
            )
        }
    }
    
    guide = guides.get(platform)
    if not guide:
        await callback.answer("Инструкция не найдена", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{guide['title']}\n\n{guide['content']}",
        reply_markup=get_back_button("install_guide"),
        parse_mode="Markdown"
    )
    await callback.answer()


# Deep link handlers for VPN clients
@router.callback_query(F.data.startswith("open_"))
async def open_vpn_client(callback: CallbackQuery):
    """Handle VPN client open requests"""
    client_name = callback.data.replace("open_", "")
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
        
        # Get VPN config
        result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = result.scalar_one_or_none()
        
        if not vpn_config or not vpn_config.config_data:
            await callback.answer("VPN конфигурация не найдена", show_alert=True)
            return
        
        # Map client names to display names
        client_display_names = {
            "v2rayng": "v2rayNG (Android)",
            "foxray": "FoXray (Android)", 
            "shadowrocket": "Shadowrocket (iOS)",
            "streisand": "Streisand (iOS)",
            "v2box": "V2Box (Cross-platform)",
            "nekobox": "NekoBox (Cross-platform)",
            "v2raytun": "v2rayTUN (Cross-platform)"
        }
        
        display_name = client_display_names.get(client_name, client_name)
        
        # Send config with instructions
        message = (
            f"📱 **Конфигурация для {display_name}**\n\n"
            f"**Шаг 1:** Скопируйте ссылку ниже\n"
            f"**Шаг 2:** Откройте приложение {display_name}\n"
            f"**Шаг 3:** Добавьте новый сервер из буфера обмена\n\n"
            f"🔗 **VLESS конфигурация:**\n"
            f"`{vpn_config.config_data}`\n\n"
            f"💡 *Нажмите и удерживайте ссылку для копирования*"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Назад к конфигурации", callback_data="get_config")
        )
        
        await callback.message.answer(
            message,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        
        await callback.answer(f"✅ Конфигурация для {display_name} отправлена!")
    
    finally:
        await session.close()


@router.callback_query(F.data == "reset_config")
async def reset_config(callback: CallbackQuery):
    """Reset VPN configuration"""
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
        
        # Get VPN config
        result = await session.execute(
            select(VPNConfig)
            .where(VPNConfig.user_id == user.id)
            .where(VPNConfig.is_active == True)
        )
        vpn_config = result.scalar_one_or_none()
        
        if not vpn_config:
            await callback.answer("VPN конфигурация не найдена", show_alert=True)
            return
        
        try:
            # Reset config in Marzban (revoke subscription)
            async with marzban_client as client:
                success = await client.revoke_user_subscription(vpn_config.marzban_user_id)
                
                if success:
                    # Get new config
                    new_config_data = await client.get_user_config(vpn_config.marzban_user_id)
                    if new_config_data:
                        vpn_config.config_data = new_config_data
                        await session.commit()
            
            await callback.answer("✅ Конфигурация сброшена", show_alert=True)
            
            # Refresh config page
            await get_config(callback)
            
        except Exception as e:
            logger.error(f"Error resetting config: {e}")
            await callback.answer("❌ Ошибка при сбросе конфигурации", show_alert=True)
    
    finally:
        await session.close()
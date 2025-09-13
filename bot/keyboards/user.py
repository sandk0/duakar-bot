from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from bot.config import settings


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu inline keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 Моя подписка", callback_data="my_subscription"),
        InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="get_config")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Оплатить/Продлить", callback_data="payment"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referral")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Поддержка", callback_data="support"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    
    return builder.as_markup()


def get_start_keyboard() -> ReplyKeyboardMarkup:
    """Get start reply keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="💳 Моя подписка"),
        KeyboardButton(text="🔑 Получить конфиг")
    )
    builder.row(
        KeyboardButton(text="💰 Оплатить"),
        KeyboardButton(text="👥 Рефералы")
    )
    builder.row(
        KeyboardButton(text="❓ Помощь")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_subscription_keyboard(has_active_subscription: bool = False) -> InlineKeyboardMarkup:
    """Get subscription management keyboard"""
    builder = InlineKeyboardBuilder()
    
    if has_active_subscription:
        builder.row(
            InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="extend_subscription")
        )
        builder.row(
            InlineKeyboardButton(text="❌ Отменить автопродление", callback_data="cancel_autorenew")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💰 Оформить подписку", callback_data="payment")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_payment_plans_keyboard() -> InlineKeyboardMarkup:
    """Get payment plans keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🆓 Пробный период", callback_data="plan_trial")
    )
    builder.row(
        InlineKeyboardButton(text="📅 1 месяц", callback_data="plan_monthly")
    )
    builder.row(
        InlineKeyboardButton(text="📅 3 месяца (-10%)", callback_data="plan_quarterly")
    )
    builder.row(
        InlineKeyboardButton(text="📅 12 месяцев (-20%)", callback_data="plan_yearly")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 У меня есть промокод", callback_data="enter_promo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    """Get payment methods keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 СБП", callback_data="pay_sbp")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Банковская карта", callback_data="pay_card")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="payment")
    )
    
    return builder.as_markup()


def get_config_keyboard(vless_url: str = None) -> InlineKeyboardMarkup:
    """Get config management keyboard with optional direct link"""
    builder = InlineKeyboardBuilder()
    
    # If we have the VLESS URL, add deep link buttons
    if vless_url and len(str(vless_url).strip()) > 0:
        
        # Add deep links as callback buttons (not URL buttons)
        # These will trigger callbacks that send the VLESS link
        
        # Row 1: Android clients
        builder.row(
            InlineKeyboardButton(
                text="📱 v2rayNG",
                callback_data="open_v2rayng"
            ),
            InlineKeyboardButton(
                text="🦊 FoXray", 
                callback_data="open_foxray"
            )
        )
        
        # Row 2: iOS clients
        builder.row(
            InlineKeyboardButton(
                text="🍎 Shadowrocket",
                callback_data="open_shadowrocket"
            ),
            InlineKeyboardButton(
                text="📦 Streisand",
                callback_data="open_streisand"
            )
        )
        
        # Row 3: Cross-platform clients
        builder.row(
            InlineKeyboardButton(
                text="📱 V2Box",
                callback_data="open_v2box"
            ),
            InlineKeyboardButton(
                text="🐱 NekoBox",
                callback_data="open_nekobox"
            )
        )
        
        # Row 4: Additional clients
        builder.row(
            InlineKeyboardButton(
                text="📲 v2rayTUN",
                callback_data="open_v2raytun"
            )
        )
    
    
    builder.row(
        InlineKeyboardButton(text="📱 Показать QR-код", callback_data="show_qr")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_link")
    )
    builder.row(
        InlineKeyboardButton(text="📖 Инструкция по установке", callback_data="install_guide")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить конфигурацию", callback_data="reset_config")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Get platform selection keyboard for installation guide"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📱 iOS", callback_data="guide_ios"),
        InlineKeyboardButton(text="🤖 Android", callback_data="guide_android")
    )
    builder.row(
        InlineKeyboardButton(text="💻 Windows", callback_data="guide_windows"),
        InlineKeyboardButton(text="🍎 macOS", callback_data="guide_macos")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="get_config")
    )
    
    return builder.as_markup()


def get_faq_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Get FAQ categories keyboard"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(text=category, callback_data=f"faq_cat_{category}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Get support keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{settings.support_username.lstrip('@')}")
    )
    builder.row(
        InlineKeyboardButton(text="🔧 Автодиагностика", callback_data="autodiagnose")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="notification_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Автопродление", callback_data="autorenew_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Get single back button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def get_cancel_button() -> InlineKeyboardMarkup:
    """Get cancel button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()
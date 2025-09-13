from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Get admin main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments"),
        InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promos")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="❓ FAQ", callback_data="admin_faq")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Тарифы", callback_data="admin_pricing"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Выйти из админки", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """Get admin users management keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_find_user")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Активные", callback_data="admin_users_active"),
        InlineKeyboardButton(text="⏰ Истекшие", callback_data="admin_users_expired")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin_users_blocked"),
        InlineKeyboardButton(text="🎁 Триал", callback_data="admin_users_trial")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Экспорт", callback_data="admin_export_users")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get user actions keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить подписку", callback_data=f"admin_edit_sub_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_block_{user_id}"),
        InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin_unblock_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Написать", callback_data=f"admin_message_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")
    )
    
    return builder.as_markup()


def get_admin_payments_keyboard() -> InlineKeyboardMarkup:
    """Get admin payments keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💸 Последние", callback_data="admin_payments_recent"),
        InlineKeyboardButton(text="❌ Неудачные", callback_data="admin_payments_failed")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_payments_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_admin_promos_keyboard() -> InlineKeyboardMarkup:
    """Get admin promo codes keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Активные", callback_data="admin_promos_active"),
        InlineKeyboardButton(text="⏰ Истекшие", callback_data="admin_promos_expired")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика использования", callback_data="admin_promos_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_promo_actions_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    """Get promo code actions keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"admin_edit_promo_{promo_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_promo_{promo_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⏸ Деактивировать", callback_data=f"admin_disable_promo_{promo_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promos")
    )
    
    return builder.as_markup()


def get_admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Get admin broadcast keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📢 Всем пользователям", callback_data="admin_broadcast_all")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Активным", callback_data="admin_broadcast_active"),
        InlineKeyboardButton(text="⏰ Истекшим", callback_data="admin_broadcast_expired")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Триал", callback_data="admin_broadcast_trial")
    )
    builder.row(
        InlineKeyboardButton(text="📋 История рассылок", callback_data="admin_broadcast_history")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_admin_faq_keyboard() -> InlineKeyboardMarkup:
    """Get admin FAQ keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="admin_add_faq")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все вопросы", callback_data="admin_faq_list")
    )
    builder.row(
        InlineKeyboardButton(text="📊 По категориям", callback_data="admin_faq_categories")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_faq_actions_keyboard(faq_id: int) -> InlineKeyboardMarkup:
    """Get FAQ item actions keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"admin_edit_faq_{faq_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_faq_{faq_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⏸ Деактивировать", callback_data=f"admin_disable_faq_{faq_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_faq")
    )
    
    return builder.as_markup()


def get_admin_pricing_keyboard() -> InlineKeyboardMarkup:
    """Get admin pricing keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Текущие тарифы", callback_data="admin_pricing_current")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить цены", callback_data="admin_edit_pricing")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Скидки", callback_data="admin_discounts")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Get admin settings keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💬 Сообщения", callback_data="admin_messages")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Реферальная система", callback_data="admin_referral_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Триал", callback_data="admin_trial_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin_notification_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def get_confirm_keyboard(action: str, item_id: str = "") -> InlineKeyboardMarkup:
    """Get confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
    )
    
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Get back to admin menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_menu")
    )
    
    return builder.as_markup()
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from typing import List


async def set_bot_commands(bot: Bot):
    """Set bot commands for different scopes"""
    
    # Commands for all users
    user_commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="menu", description="📱 Главное меню"),
        BotCommand(command="subscription", description="💳 Управление подпиской"),
        BotCommand(command="pay", description="💰 Оплатить подписку"),
        BotCommand(command="config", description="🔑 Получить конфигурацию VPN"),
        BotCommand(command="referral", description="👥 Реферальная программа"),
        BotCommand(command="support", description="💬 Поддержка"),
        BotCommand(command="faq", description="❓ Часто задаваемые вопросы"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="cancel", description="❌ Отмена текущего действия")
    ]
    
    await bot.set_my_commands(
        commands=user_commands,
        scope=BotCommandScopeDefault()
    )
    

async def set_admin_commands(bot: Bot, admin_user_id: int):
    """Set additional commands for admin users"""
    admin_commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="menu", description="📱 Главное меню"),
        BotCommand(command="subscription", description="💳 Управление подпиской"),
        BotCommand(command="config", description="🔑 Получить конфигурацию VPN"),
        BotCommand(command="referral", description="👥 Реферальная программа"),
        BotCommand(command="support", description="💬 Поддержка"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="cancel", description="❌ Отмена текущего действия"),
        # Admin commands
        BotCommand(command="admin", description="🔧 Админ панель"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="broadcast", description="📢 Рассылка"),
        BotCommand(command="users", description="👤 Управление пользователями"),
        BotCommand(command="payments", description="💰 Управление платежами"),
        BotCommand(command="settings", description="⚙️ Настройки системы"),
        BotCommand(command="logs", description="📋 Логи системы"),
        BotCommand(command="reset_trial", description="🔄 Сбросить пробный период")
    ]
    
    await bot.set_my_commands(
        commands=admin_commands,
        scope=BotCommandScopeChat(chat_id=admin_user_id)
    )
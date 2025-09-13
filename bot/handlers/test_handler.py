from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("test"))
async def test_command(message: Message, **kwargs):
    """Simple test command"""
    await message.answer(f"✅ Тест успешен! Ваш Telegram ID: {message.from_user.id}")

# Removed echo handler to avoid intercepting other commands
# @router.message()
# async def echo_handler(message: Message, **kwargs):
#     """Echo any message for testing"""
#     if message.text and not message.text.startswith("/"):
#         await message.answer(f"Получено сообщение: {message.text}")
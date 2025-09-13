from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from bot.keyboards.user import get_back_button
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "faq")
@router.message(Command("faq"))
async def show_faq(event: Message | CallbackQuery):
    """Show FAQ"""
    
    faq_text = """
❓ **Часто задаваемые вопросы**

**1. Как начать пользоваться VPN?**
• Оформите подписку через /subscription
• Получите конфигурацию через /config
• Установите приложение для вашего устройства
• Импортируйте конфигурацию в приложение

**2. Какие приложения использовать?**
📱 **iOS:** Streisand, V2Box
🤖 **Android:** v2rayNG, Hiddify
💻 **Windows:** Nekoray, v2rayN
🍎 **macOS:** V2Box, Qv2ray

**3. Что такое пробный период?**
Бесплатный 7-дневный доступ для новых пользователей. Позволяет протестировать качество сервиса перед оплатой.

**4. Как работает реферальная программа?**
За каждого приглашенного друга, оплатившего подписку, вы получаете 7 бонусных дней к вашей подписке.

**5. Какие способы оплаты доступны?**
• Банковские карты (Visa, MasterCard, МИР)
• СБП (Система быстрых платежей)
• Электронные кошельки

**6. Можно ли использовать на нескольких устройствах?**
Да, одну конфигурацию можно использовать на 3 устройствах одновременно.

**7. Что делать если VPN не работает?**
• Проверьте срок действия подписки
• Обновите конфигурацию через /config
• Попробуйте другое приложение
• Обратитесь в поддержку /support

**8. Как отменить подписку?**
Автопродление можно отключить в разделе "Моя подписка". Доступ сохранится до конца оплаченного периода.

**9. Безопасно ли это?**
Мы используем современные протоколы шифрования (VLESS + Reality), не храним логи и не отслеживаем вашу активность.

**10. Работает ли с мобильным интернетом?**
Да, наши конфигурации оптимизированы для обхода блокировок мобильных операторов (МТС, Мегафон, Билайн, Теле2).

💬 Не нашли ответ? Напишите в /support
"""
    
    if isinstance(event, Message):
        await event.answer(faq_text, parse_mode="Markdown", reply_markup=get_back_button())
    else:
        await event.message.edit_text(faq_text, parse_mode="Markdown", reply_markup=get_back_button())
        await event.answer()
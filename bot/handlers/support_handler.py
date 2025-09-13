from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.models import User, FAQItem, Subscription, SubscriptionStatus, VPNConfig
from database.connection import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from bot.keyboards.user import get_faq_keyboard, get_support_keyboard, get_back_button
from services.marzban import marzban_client
from bot.config import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("support"))
@router.callback_query(F.data == "support")
async def show_support(event: Message | CallbackQuery):
    """Show support options"""
    text = (
        f"💬 **Поддержка**\n\n"
        f"Выберите удобный способ получения помощи:\n\n"
        f"🤖 **Автодиагностика** - автоматическая проверка вашего подключения\n"
        f"👨‍💻 **Написать в поддержку** - связь с оператором\n\n"
        f"⏰ **Время работы поддержки:** 10:00 - 22:00 (МСК)\n"
        f"📞 **Среднее время ответа:** до 2 часов"
    )
    
    if isinstance(event, Message):
        await event.answer(
            text,
            reply_markup=get_support_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await event.message.edit_text(
            text,
            reply_markup=get_support_keyboard(),
            parse_mode="Markdown"
        )
        await event.answer()


@router.message(Command("faq"))
@router.callback_query(F.data == "faq")
async def show_faq(event: Message | CallbackQuery):
    """Show FAQ categories"""
    # Create database session
    session = async_session_maker()
    try:
        # Get FAQ items from database
        result = await session.execute(
            select(FAQItem).where(FAQItem.is_active == True).order_by(FAQItem.order_index)
        )
        faq_items = result.scalars().all()
        
        if not faq_items:
            text = "❌ Пока нет вопросов в FAQ"
            if isinstance(event, Message):
                await event.answer(text)
            else:
                await event.message.edit_text(text)
                await event.answer()
            return
        
        # Get FAQ categories
        result = await session.execute(
            select(FAQItem.category)
            .where(FAQItem.is_active == True)
            .distinct()
            .order_by(FAQItem.category)
        )
        categories = [row[0] for row in result.all() if row[0]]
        
        if not categories:
            # Create default FAQ if none exists
            await create_default_faq(session)
            categories = ["Подключение", "Оплата", "Технические вопросы"]
        
        text = (
            f"❓ **Часто задаваемые вопросы**\n\n"
            f"Выберите категорию, чтобы найти ответ на ваш вопрос:"
        )
        
        if isinstance(event, Message):
            await event.answer(
                text,
                reply_markup=get_faq_keyboard(categories),
                parse_mode="Markdown"
            )
        else:
            await event.message.edit_text(
                text,
                reply_markup=get_faq_keyboard(categories),
                parse_mode="Markdown"
            )
            await event.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data.startswith("faq_cat_"))
async def show_faq_category(callback: CallbackQuery):
    """Show FAQ items for specific category"""
    # Create database session
    session = async_session_maker()
    try:
        category = callback.data.replace("faq_cat_", "")
        
        # Get FAQ items for category
        result = await session.execute(
            select(FAQItem)
            .where(
                and_(
                    FAQItem.category == category,
                    FAQItem.is_active == True
                )
            )
            .order_by(FAQItem.order_index)
        )
        faq_items = result.scalars().all()
        
        if not faq_items:
            await callback.answer("В этой категории пока нет вопросов", show_alert=True)
            return
        
        text = f"❓ **{category}**\n\n"
        
        for i, item in enumerate(faq_items, 1):
            text += f"**{i}. {item.question}**\n{item.answer}\n\n"
        
        # Limit text length
        if len(text) > 4000:
            text = text[:4000] + "...\n\nДля получения полной информации обратитесь в поддержку."
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("faq"),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data == "autodiagnose")
async def autodiagnose(callback: CallbackQuery):
    """Perform automatic diagnosis"""
    telegram_user_id = callback.from_user.id
    
    # Create database session
    session = async_session_maker()
    try:
        await callback.answer("Выполняю диагностику...")
    
        # Get user first
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "❌ Пользователь не найден в системе",
                reply_markup=get_back_button("support")
            )
            return
        
        diagnosis_results = []
        
        # Check subscription status
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]))
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            diagnosis_results.append("❌ **Подписка:** Отсутствует активная подписка")
            recommendations = [
                "• Оформите подписку для доступа к VPN",
                "• Проверьте статус оплаты в разделе 'Моя подписка'"
            ]
        elif subscription.end_date <= datetime.now():
            diagnosis_results.append("⚠️ **Подписка:** Истекла")
            recommendations = [
                "• Продлите подписку в разделе 'Оплатить/Продлить'",
                "• Проверьте настройки автопродления"
            ]
        else:
            days_left = (subscription.end_date - datetime.now()).days
            diagnosis_results.append(f"✅ **Подписка:** Активна ({days_left} дн.)")
            recommendations = []
        
        # Check VPN config
        if subscription:
            result = await session.execute(
                select(VPNConfig)
                .where(VPNConfig.user_id == user.id)
                .where(VPNConfig.is_active == True)
            )
            vpn_config = result.scalar_one_or_none()
            
            if not vpn_config:
                diagnosis_results.append("❌ **VPN конфигурация:** Не найдена")
                recommendations.extend([
                    "• Перейдите в раздел 'Получить конфиг'",
                    "• Попробуйте сбросить конфигурацию"
                ])
            else:
                diagnosis_results.append("✅ **VPN конфигурация:** Найдена")
        
        # Check Marzban server status
        try:
            async with marzban_client as client:
                stats = await client.get_system_stats()
                diagnosis_results.append("✅ **VPN сервер:** Доступен")
                
                # Check user status in Marzban
                if subscription and vpn_config:
                    marzban_user = await client.get_user(vpn_config.marzban_user_id)
                    if marzban_user:
                        if marzban_user.status.value == "active":
                            diagnosis_results.append("✅ **Статус в системе:** Активен")
                        else:
                            diagnosis_results.append(f"⚠️ **Статус в системе:** {marzban_user.status.value}")
                            recommendations.append("• Обратитесь в поддержку для активации")
                    else:
                        diagnosis_results.append("❌ **Пользователь в системе:** Не найден")
                        recommendations.append("• Обратитесь в поддержку для восстановления доступа")
        
        except Exception as e:
            diagnosis_results.append("❌ **VPN сервер:** Недоступен")
            recommendations.extend([
                "• Попробуйте подключиться позже",
                "• Обратитесь в поддержку, если проблема не решается"
            ])
            logger.error(f"Marzban connection error during diagnosis: {e}")
        
        # Compile diagnosis report
        text = "🔧 **Результаты диагностики**\n\n"
        text += "\n".join(diagnosis_results)
        
        if recommendations:
            text += "\n\n💡 **Рекомендации:**\n"
            text += "\n".join(recommendations)
        else:
            text += "\n\n✅ **Все проверки пройдены успешно!**\n"
            text += "Если у вас все еще есть проблемы с подключением, попробуйте:\n"
            text += "• Перезапустить VPN приложение\n"
            text += "• Проверить интернет соединение\n"
            text += "• Попробовать другой VPN протокол"
        
        text += f"\n\n📅 **Время диагностики:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("support"),
            parse_mode="Markdown"
        )
        
    finally:
        await session.close()


async def create_default_faq(session: AsyncSession):
    """Create default FAQ items"""
    default_faq = [
        {
            "category": "Подключение",
            "items": [
                {
                    "question": "Как подключиться к VPN?",
                    "answer": "1. Получите конфигурацию в разделе 'Получить конфиг'\n2. Скачайте VPN клиент для вашего устройства\n3. Импортируйте конфигурацию в приложение\n4. Нажмите кнопку подключения"
                },
                {
                    "question": "Какие приложения поддерживаются?",
                    "answer": "iOS: Shadowrocket, OneClick\nAndroid: v2rayNG, Clash\nWindows: v2rayN, Clash for Windows\nmacOS: ClashX, V2RayX"
                },
                {
                    "question": "VPN не подключается, что делать?",
                    "answer": "1. Проверьте статус подписки\n2. Обновите конфигурацию\n3. Попробуйте другой VPN клиент\n4. Перезагрузите устройство\n5. Свяжитесь с поддержкой"
                }
            ]
        },
        {
            "category": "Оплата",
            "items": [
                {
                    "question": "Как оплатить подписку?",
                    "answer": "1. Перейдите в раздел 'Оплатить/Продлить'\n2. Выберите тарифный план\n3. Выберите способ оплаты\n4. Перейдите по ссылке и завершите оплату"
                },
                {
                    "question": "Какие способы оплаты доступны?",
                    "answer": "• Банковские карты (Visa, MasterCard, МИР)\n• СБП (Система быстрых платежей)\n• ЮMoney\n• QIWI"
                },
                {
                    "question": "Когда активируется подписка?",
                    "answer": "Подписка активируется автоматически в течение 1-5 минут после успешной оплаты. Если активация не произошла, обратитесь в поддержку."
                }
            ]
        },
        {
            "category": "Технические вопросы",
            "items": [
                {
                    "question": "На скольких устройствах можно использовать?",
                    "answer": "Одна подписка работает только на одном устройстве одновременно. При подключении нового устройства предыдущее автоматически отключается."
                },
                {
                    "question": "Есть ли ограничения по трафику?",
                    "answer": "Нет, все тарифы предоставляют безлимитный трафик без ограничений скорости."
                },
                {
                    "question": "Как посмотреть статистику использования?",
                    "answer": "Статистика доступна в разделе 'Статистика' главного меню. Там вы можете увидеть использованный трафик и время подключения."
                }
            ]
        }
    ]
    
    order_index = 0
    for category_data in default_faq:
        category = category_data["category"]
        for item_data in category_data["items"]:
            faq_item = FAQItem(
                question=item_data["question"],
                answer=item_data["answer"],
                category=category,
                order_index=order_index,
                is_active=True
            )
            session.add(faq_item)
            order_index += 1
    
    await session.commit()
    logger.info("Default FAQ created")
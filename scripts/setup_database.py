#!/usr/bin/env python3
"""
Setup database with initial data
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import async_session_maker, init_db
from database.models import PricingPlan, SystemSetting, FAQItem
from decimal import Decimal
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_default_pricing():
    """Create default pricing plans"""
    try:
        async with async_session_maker() as session:
            # Check if pricing plans already exist
            from sqlalchemy import select, func
            
            count = await session.scalar(select(func.count(PricingPlan.id)))
            if count > 0:
                logger.info("Pricing plans already exist, skipping...")
                return
            
            plans = [
                {
                    "name": "monthly",
                    "duration_days": 30,
                    "price": Decimal("299.00"),
                    "discount_percent": Decimal("0.00"),
                    "features": {"unlimited_traffic": True, "one_device": True}
                },
                {
                    "name": "quarterly", 
                    "duration_days": 90,
                    "price": Decimal("799.00"),
                    "discount_percent": Decimal("10.00"),
                    "features": {"unlimited_traffic": True, "one_device": True}
                },
                {
                    "name": "yearly",
                    "duration_days": 365,
                    "price": Decimal("2999.00"),
                    "discount_percent": Decimal("20.00"),
                    "features": {"unlimited_traffic": True, "one_device": True}
                }
            ]
            
            for plan_data in plans:
                plan = PricingPlan(
                    name=plan_data["name"],
                    duration_days=plan_data["duration_days"],
                    price=plan_data["price"],
                    discount_percent=plan_data["discount_percent"],
                    is_active=True,
                    features=json.dumps(plan_data["features"])
                )
                session.add(plan)
            
            await session.commit()
            logger.info(f"Created {len(plans)} pricing plans")
    
    except Exception as e:
        logger.error(f"Error creating pricing plans: {e}")
        raise


async def create_system_settings():
    """Create default system settings"""
    try:
        async with async_session_maker() as session:
            settings = [
                {
                    "key": "bot_settings",
                    "value": {
                        "welcome_message": "👋 Добро пожаловать в VPN Bot!",
                        "support_username": "@support",
                        "trial_days": 7,
                        "referral_bonus_days": 30,
                        "referral_friend_bonus_days": 7
                    }
                },
                {
                    "key": "payment_settings",
                    "value": {
                        "auto_renewal": True,
                        "retry_failed_payments": True,
                        "notification_days": [1, 2, 3]
                    }
                },
                {
                    "key": "vpn_settings",
                    "value": {
                        "protocol": "vless",
                        "max_devices_per_user": 1,
                        "sync_interval_minutes": 30
                    }
                }
            ]
            
            from sqlalchemy import select
            
            for setting_data in settings:
                # Check if setting exists
                result = await session.execute(
                    select(SystemSetting).where(SystemSetting.key == setting_data["key"])
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    setting = SystemSetting(
                        key=setting_data["key"],
                        value=json.dumps(setting_data["value"])
                    )
                    session.add(setting)
                    logger.info(f"Created system setting: {setting_data['key']}")
            
            await session.commit()
    
    except Exception as e:
        logger.error(f"Error creating system settings: {e}")
        raise


async def create_default_faq():
    """Create default FAQ items"""
    try:
        async with async_session_maker() as session:
            from sqlalchemy import select, func
            
            count = await session.scalar(select(func.count(FAQItem.id)))
            if count > 0:
                logger.info("FAQ items already exist, skipping...")
                return
            
            faq_items = [
                {
                    "category": "Подключение",
                    "question": "Как подключиться к VPN?",
                    "answer": "1. Получите конфигурацию в разделе 'Получить конфиг'\n2. Скачайте VPN клиент для вашего устройства\n3. Импортируйте конфигурацию в приложение\n4. Нажмите кнопку подключения",
                    "order_index": 1
                },
                {
                    "category": "Подключение",
                    "question": "Какие приложения поддерживаются?",
                    "answer": "iOS: Shadowrocket, OneClick\nAndroid: v2rayNG, Clash\nWindows: v2rayN, Clash for Windows\nmacOS: ClashX, V2RayX",
                    "order_index": 2
                },
                {
                    "category": "Подключение",
                    "question": "VPN не подключается, что делать?",
                    "answer": "1. Проверьте статус подписки\n2. Обновите конфигурацию\n3. Попробуйте другой VPN клиент\n4. Перезагрузите устройство\n5. Свяжитесь с поддержкой",
                    "order_index": 3
                },
                {
                    "category": "Оплата",
                    "question": "Как оплатить подписку?",
                    "answer": "1. Перейдите в раздел 'Оплатить/Продлить'\n2. Выберите тарифный план\n3. Выберите способ оплаты\n4. Перейдите по ссылке и завершите оплату",
                    "order_index": 4
                },
                {
                    "category": "Оплата",
                    "question": "Какие способы оплаты доступны?",
                    "answer": "• Банковские карты (Visa, MasterCard, МИР)\n• СБП (Система быстрых платежей)\n• ЮMoney\n• QIWI",
                    "order_index": 5
                },
                {
                    "category": "Оплата",
                    "question": "Когда активируется подписка?",
                    "answer": "Подписка активируется автоматически в течение 1-5 минут после успешной оплаты. Если активация не произошла, обратитесь в поддержку.",
                    "order_index": 6
                },
                {
                    "category": "Технические вопросы",
                    "question": "На скольких устройствах можно использовать?",
                    "answer": "Одна подписка работает только на одном устройстве одновременно. При подключении нового устройства предыдущее автоматически отключается.",
                    "order_index": 7
                },
                {
                    "category": "Технические вопросы",
                    "question": "Есть ли ограничения по трафику?",
                    "answer": "Нет, все тарифы предоставляют безлимитный трафик без ограничений скорости.",
                    "order_index": 8
                },
                {
                    "category": "Технические вопросы",
                    "question": "Как посмотреть статистику использования?",
                    "answer": "Статистика доступна в разделе 'Статистика' главного меню. Там вы можете увидеть использованный трафик и время подключения.",
                    "order_index": 9
                }
            ]
            
            for faq_data in faq_items:
                faq_item = FAQItem(
                    category=faq_data["category"],
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    order_index=faq_data["order_index"],
                    is_active=True
                )
                session.add(faq_item)
            
            await session.commit()
            logger.info(f"Created {len(faq_items)} FAQ items")
    
    except Exception as e:
        logger.error(f"Error creating FAQ items: {e}")
        raise


async def main():
    """Main setup function"""
    try:
        logger.info("Starting database setup...")
        
        # Initialize database tables
        await init_db()
        logger.info("✅ Database tables created")
        
        # Create default pricing plans
        await create_default_pricing()
        logger.info("✅ Default pricing plans created")
        
        # Create system settings
        await create_system_settings()
        logger.info("✅ System settings created")
        
        # Create default FAQ
        await create_default_faq()
        logger.info("✅ Default FAQ items created")
        
        logger.info("\n🎉 Database setup completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Create admin user: python scripts/init_admin.py <your_telegram_id>")
        logger.info("2. Configure .env file with your API keys")
        logger.info("3. Start the bot: make up")
    
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
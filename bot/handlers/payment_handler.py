from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import User, Subscription, Payment, PricingPlan, PromoCode, PromoUsage, SubscriptionStatus
from database.models.payment import PaymentStatus as DBPaymentStatus, PaymentMethod as DBPaymentMethod, PaymentSystem
from database.connection import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from bot.keyboards.user import (
    get_payment_plans_keyboard, get_payment_methods_keyboard, 
    get_back_button, get_cancel_button
)
from bot.states.payment import PaymentStates
from services.payment import payment_manager, PaymentMethod
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)
router = Router()


# Default pricing (can be overridden by admin)
DEFAULT_PRICES = {
    "Пробный период": {"price": Decimal("0"), "days": 7, "discount": 0},
    "monthly": {"price": Decimal("299"), "days": 30, "discount": 0},
    "quarterly": {"price": Decimal("799"), "days": 90, "discount": 10},
    "yearly": {"price": Decimal("2999"), "days": 365, "discount": 20}
}


@router.message(Command("pay"))
@router.callback_query(F.data == "payment")
async def show_payment_plans(event: Message | CallbackQuery):
    """Show payment plans"""
    
    # Create database session
    session = async_session_maker()
    try:
        # Get pricing plans from database
        result = await session.execute(
            select(PricingPlan).where(PricingPlan.is_active == True)
        )
        db_plans = result.scalars().all()
        
        # Use database plans or defaults
        if db_plans:
            plans = {plan.name: {
                "price": plan.price,
                "days": plan.duration_days,
                "discount": 0  # No discount field in PricingPlan model
            } for plan in db_plans}
        else:
            plans = DEFAULT_PRICES
        
        text = "💰 **Выберите тарифный план:**\n\n"
        
        for plan_name, plan_data in plans.items():
            price = plan_data["price"]
            days = plan_data["days"]
            discount = plan_data["discount"]
            
            if plan_name == "Пробный период":
                plan_title = "🆓 Пробный период (7 дней)"
            elif plan_name == "monthly":
                plan_title = "📅 1 месяц"
            elif plan_name == "quarterly":
                plan_title = "📅 3 месяца"
                if discount > 0:
                    plan_title += f" (-{discount}%)"
            elif plan_name == "yearly":
                plan_title = "📅 12 месяцев"
                if discount > 0:
                    plan_title += f" (-{discount}%)"
            else:
                plan_title = f"📅 {plan_name}"
            
            if plan_name == "Пробный период":
                text += f"{plan_title}: **БЕСПЛАТНО**\n"
            else:
                text += f"{plan_title}: **{price} ₽**\n"
        
        text += "\n🎁 Есть промокод? Нажмите соответствующую кнопку!"
        
        # Create dynamic keyboard based on actual plans
        keyboard = create_dynamic_payment_keyboard(plans)
        
        if isinstance(event, Message):
            await event.answer(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await event.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await event.answer()
    
    finally:
        await session.close()


@router.callback_query(F.data.startswith("plan_"))
async def select_payment_plan(callback: CallbackQuery, state: FSMContext):
    """Handle plan selection"""
    print(f"=== PAYMENT HANDLER DEBUG: select_payment_plan called with {callback.data} ===")
    logger.info(f"select_payment_plan called with data: {callback.data}")
    # Create database session
    async_session = async_session_maker()
    
    try:
        plan_type = callback.data.replace("plan_", "")
        
        # Handle plan name mapping
        if plan_type == "trial":
            db_plan_name = "Пробный период"
        elif plan_type == "monthly":
            db_plan_name = "Месячная подписка"
        elif plan_type == "quarterly":
            db_plan_name = "Квартальная подписка"
        elif plan_type == "yearly":
            db_plan_name = "Годовая подписка"
        else:
            db_plan_name = plan_type
        
        # Get plan details
        result = await async_session.execute(
            select(PricingPlan).where(
                and_(
                    PricingPlan.name == db_plan_name,
                    PricingPlan.is_active == True
                )
            )
        )
        db_plan = result.scalar_one_or_none()
        
        if db_plan:
            price = db_plan.price
            days = db_plan.duration_days
            discount = 0  # No discount field in PricingPlan model
            plan_type = db_plan.name  # Use actual database name
            logger.info(f"Found DB plan: {db_plan.name}, setting plan_type to: '{plan_type}'")
        else:
            # Fallback to DEFAULT_PRICES with mapping
            if plan_type == "trial":
                plan_data = DEFAULT_PRICES.get("Пробный период")
                plan_type = "Пробный период"
            else:
                plan_data = DEFAULT_PRICES.get(plan_type)
            
            if not plan_data:
                await callback.answer("Неверный тарифный план", show_alert=True)
                return
            price = plan_data["price"]
            days = plan_data["days"]
            discount = plan_data["discount"]
        
        # Save selected plan to FSM
        await state.update_data(
            plan_type=plan_type,
            price=float(price),
            days=days,
            discount=discount
        )
        
        # Format plan name
        if plan_type == "Пробный период" or plan_type == "trial":
            plan_name = "Пробный период (7 дней)"
        elif plan_type == "monthly":
            plan_name = "1 месяц"
        elif plan_type == "quarterly":
            plan_name = "3 месяца"
        elif plan_type == "yearly":
            plan_name = "12 месяцев"
        else:
            plan_name = plan_type
        
        # Handle trial plan - activate immediately without payment
        logger.info(f"Checking if plan_type '{plan_type}' is trial plan...")
        if plan_type == "Пробный период" or plan_type == "trial":
            # Check if user already used trial
            user_result = await async_session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # User not found - create new user
                logger.info(f"User {callback.from_user.id} not found, creating new user for trial")
                try:
                    user = User(
                        telegram_id=callback.from_user.id,
                        username=callback.from_user.username,
                        first_name=callback.from_user.first_name,
                        last_name=callback.from_user.last_name,
                        language_code=callback.from_user.language_code,
                        trial_used=False
                    )
                    async_session.add(user)
                    await async_session.commit()
                    await async_session.refresh(user)
                    logger.info(f"Created new user with id {user.id} for telegram_id {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to create user for {callback.from_user.id}: {e}")
                    await callback.answer("Ошибка создания пользователя", show_alert=True)
                    return
            
            if user.trial_used:
                await callback.message.edit_text(
                    "❌ **Пробный период уже использован**\n\n"
                    "Каждый пользователь может воспользоваться пробным периодом только один раз.\n"
                    "Выберите другой тарифный план:",
                    reply_markup=get_payment_plans_keyboard(),
                    parse_mode="Markdown"
                )
                await callback.answer("Пробный период уже использован")
                return
            
            # Activate trial subscription immediately
            if user:
                await activate_trial_subscription(callback, user, async_session, days)
            else:
                logger.error(f"User is None for telegram_id {callback.from_user.id}, cannot activate trial")
                await callback.answer("Ошибка активации пробного периода", show_alert=True)
            return
        
        text = (
            f"💳 **Оплата подписки**\n\n"
            f"Тариф: {plan_name}\n"
            f"Срок: {days} дней\n"
            f"Цена: **{price} ₽**\n"
        )
        
        if discount > 0:
            original_price = price / (1 - discount / 100)
            text += f"Скидка: {discount}% (экономия {original_price - price:.0f} ₽)\n"
        
        text += "\nВыберите способ оплаты:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_methods_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer("✅ План выбран! Выберите способ оплаты.")
        
    finally:
        await async_session.close()


@router.callback_query(F.data == "enter_promo")
async def enter_promo_code(callback: CallbackQuery, state: FSMContext):
    """Enter promo code"""
    await state.set_state(PaymentStates.entering_promo)
    
    await callback.message.edit_text(
        "🎁 **Введите промокод:**\n\n"
        "Отправьте сообщение с вашим промокодом",
        reply_markup=get_cancel_button(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(PaymentStates.entering_promo)
async def process_promo_code(message: Message, state: FSMContext):
    """Process promo code"""
    async_session = async_session_maker()
    telegram_user_id = message.from_user.id
    
    try:
        # Get user first
        user_result = await async_session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "❌ Пользователь не найден",
                reply_markup=get_back_button("payment")
            )
            return
        
        promo_code = message.text.strip().upper()
        
        # Check if promo code exists and is valid
        result = await async_session.execute(
            select(PromoCode).where(
                and_(
                    PromoCode.code == promo_code,
                    PromoCode.is_active == True,
                    PromoCode.valid_from <= datetime.now(),
                    PromoCode.valid_until >= datetime.now()
                )
            )
        )
        promo = result.scalar_one_or_none()
        
        if not promo:
            await message.answer(
                "❌ **Промокод не найден или недействителен**\n\n"
                "Проверьте правильность ввода промокода",
                reply_markup=get_back_button("enter_promo"),
                parse_mode="Markdown"
            )
            return
        
        # Check usage limits
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            await message.answer(
                "❌ **Промокод исчерпан**\n\n"
                "Этот промокод больше недоступен для использования",
                reply_markup=get_back_button("payment"),
                parse_mode="Markdown"
            )
            return
        
        # Check if user already used this promo
        result = await async_session.execute(
            select(PromoUsage).where(
                and_(
                    PromoUsage.user_id == user.id,
                    PromoUsage.promo_code_id == promo.id
                )
            )
        )
        existing_usage = result.scalar_one_or_none()
        
        if existing_usage:
            await message.answer(
                "❌ **Промокод уже использован**\n\n"
                "Вы уже использовали этот промокод ранее",
                reply_markup=get_back_button("payment"),
                parse_mode="Markdown"
            )
            return
        
        # Save promo to FSM data
        await state.update_data(promo_code=promo_code, promo_id=promo.id)
        
        # Clear state
        await state.clear()
        
        await message.answer(
            f"✅ **Промокод применен: {promo_code}**\n\n"
            f"Скидка: {promo.value}{'%' if promo.type == 'percent' else ' ₽'}\n\n"
            "Теперь выберите тарифный план:",
            reply_markup=get_payment_plans_keyboard(),
            parse_mode="Markdown"
        )
        
    finally:
        await async_session.close()


@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    """Process payment with selected method"""
    async_session = async_session_maker()
    telegram_user_id = callback.from_user.id
    
    try:
        # Get user first
        user_result = await async_session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        method_str = callback.data.replace("pay_", "")
        
        # Check if in testing mode - skip payments
        try:
            from bot.config import settings
            if getattr(settings, 'testing_mode', False):
                await process_testing_mode_payment(callback, user, async_session, state)
                return
        except:
            pass
        
        # Map callback data to payment method
        method_mapping = {
            "sbp": PaymentMethod.SBP,
            "card": PaymentMethod.CARD,
            "yoomoney": PaymentMethod.YOOMONEY
        }
        
        payment_method = method_mapping.get(method_str)
        if not payment_method:
            await callback.answer("Неподдерживаемый способ оплаты", show_alert=True)
            return
        
        # Get FSM data
        fsm_data = await state.get_data()
        
        if not fsm_data.get("plan_type"):
            await callback.answer("Выберите тарифный план", show_alert=True)
            await show_payment_plans(callback)
            return
        
        plan_type = fsm_data["plan_type"]
        price = Decimal(str(fsm_data["price"]))
        days = fsm_data["days"]
        promo_code = fsm_data.get("promo_code")
        promo_id = fsm_data.get("promo_id")
        
        # Apply promo code discount if present
        final_price = price
        if promo_id:
            result = await async_session.execute(
                select(PromoCode).where(PromoCode.id == promo_id)
            )
            promo = result.scalar_one_or_none()
            
            if promo:
                if promo.type == "percent":
                    final_price = price * (1 - promo.value / 100)
                elif promo.type == "fixed":
                    final_price = max(price - promo.value, Decimal("1"))
        
        # Create order ID
        order_id = f"vpn_{user.telegram_id}_{int(datetime.now().timestamp())}"
        
        # Create payment in database
        db_payment = Payment(
            user_id=user.id,
            amount=final_price,
            currency="RUB",
            payment_method=method_str,
            status=DBPaymentStatus.PENDING,
            description=f"VPN подписка ({plan_type}) - {days} дней"
        )
        async_session.add(db_payment)
        await async_session.flush()  # Get payment ID
        
        # Create payment via payment manager
        payment_response, provider_name = await payment_manager.create_payment(
            amount=final_price,
            description=f"VPN подписка - {days} дней",
            order_id=order_id,
            method=payment_method,
            customer_email=None,
            webhook_url=f"https://yourbot.com/webhook/payment/{provider_name}",
            metadata={
                "user_id": str(user.id),
                "telegram_id": str(user.telegram_id),
                "plan_type": plan_type,
                "days": str(days),
                "promo_code": promo_code or "",
                "db_payment_id": str(db_payment.id)
            }
        )
        
        # Update payment with external info
        db_payment.external_payment_id = payment_response.payment_id
        db_payment.payment_system = provider_name
        
        await async_session.commit()
        
        # Send payment link to user
        await callback.message.edit_text(
            f"💳 **Оплата подписки**\n\n"
            f"Тариф: {plan_type}\n"
            f"Сумма: **{final_price} ₽**\n"
            f"Способ: {method_str.upper()}\n\n"
            f"🔗 [Перейти к оплате]({payment_response.payment_url})\n\n"
            f"После успешной оплаты ваша подписка будет активирована автоматически.",
            parse_mode="Markdown",
            reply_markup=get_back_button("payment")
        )
        
        await callback.answer("Ссылка на оплату создана")
        
        # Clear FSM state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await callback.answer(
            "❌ Ошибка создания платежа. Попробуйте позже.",
            show_alert=True
        )
        
    finally:
        await async_session.close()


@router.callback_query(F.data == "cancel")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Cancel payment process"""
    await state.clear()
    await callback.message.edit_text(
        "❌ **Операция отменена**\n\n"
        "Вы можете вернуться к выбору тарифов в любое время",
        reply_markup=get_back_button("main_menu"),
        parse_mode="Markdown"
    )
    await callback.answer()


async def process_testing_mode_payment(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    """Process payment in testing mode - skip actual payment"""
    try:
        # Get FSM data
        fsm_data = await state.get_data()
        
        if not fsm_data.get("plan_type"):
            await callback.answer("Выберите тарифный план", show_alert=True)
            return
        
        plan_type = fsm_data["plan_type"]
        days = fsm_data["days"]
        price = Decimal(str(fsm_data["price"]))
        
        # Create fake successful payment
        fake_payment = Payment(
            user_id=user.id,
            amount=price,
            currency="RUB",
            payment_method="testing",
            payment_system="testing",
            status=DBPaymentStatus.SUCCESS,
            external_payment_id=f"test_{user.telegram_id}_{int(datetime.now().timestamp())}",
            description=f"TESTING MODE: VPN подписка ({plan_type}) - {days} дней"
        )
        async_session.add(fake_payment)
        await async_session.flush()
        
        # Create/extend subscription
        result = await async_session.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user.id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                )
            )
            .order_by(Subscription.created_at.desc())
        )
        current_subscription = result.scalar_one_or_none()
        
        now = datetime.now()
        if current_subscription and current_subscription.end_date > now:
            # Extend existing subscription
            current_subscription.end_date = current_subscription.end_date + timedelta(days=days)
            new_subscription = current_subscription
        else:
            # Create new subscription
            if current_subscription:
                current_subscription.status = SubscriptionStatus.EXPIRED
            
            # Get plan ID from database
            from sqlalchemy import select
            plan_result = await session.execute(
                select(PricingPlan).where(PricingPlan.name == plan_type)
            )
            plan = plan_result.scalar_one_or_none()
            
            if not plan:
                # Fallback - try to find any plan or use default
                plan_result = await session.execute(
                    select(PricingPlan).where(PricingPlan.is_active == True).limit(1)
                )
                plan = plan_result.scalar_one_or_none()
                if not plan:
                    await callback.answer("❌ Планы не найдены", show_alert=True)
                    return
            
            new_subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=now,
                end_date=now + timedelta(days=days),
                auto_renew=False  # Disable auto-renewal in testing
            )
            async_session.add(new_subscription)
        
        fake_payment.subscription_id = new_subscription.id
        
        # Ensure VPN config exists and is active
        await ensure_vpn_config_for_testing(user, session)
        
        await async_session.commit()
        
        await callback.message.edit_text(
            f"🧪 **ТЕСТОВЫЙ РЕЖИМ - Подписка активирована!**\n\n"
            f"💳 Тариф: {plan_type}\n"
            f"📅 Период: {days} дней\n"
            f"💰 Сумма: {price} ₽ (не списано)\n\n"
            f"✅ Ваша VPN подписка активна!\n"
            f"🔑 Получите конфигурацию: /config\n\n"
            f"⚠️ Это тестовый режим - реальные платежи не проводятся",
            reply_markup=get_back_button("main_menu"),
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Тестовая подписка активирована!")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in testing mode payment: {e}")
        await callback.answer("❌ Ошибка активации тестовой подписки", show_alert=True)


async def ensure_vpn_config_for_testing(user: User, session: AsyncSession):
    """Ensure VPN config exists for testing user"""
    try:
        from database.models import VPNConfig
        from services.marzban import marzban_client, generate_unique_username
        
        # Check if user already has VPN config
        result = await async_session.execute(
            select(VPNConfig).where(VPNConfig.user_id == user.id)
        )
        vpn_config = result.scalar_one_or_none()
        
        if vpn_config:
            # Reactivate existing config
            vpn_config.is_active = True
        else:
            # Create new VPN config
            async with marzban_client as client:
                marzban_username = generate_unique_username(user.telegram_id)
                marzban_user = await client.create_user(
                    username=marzban_username,
                    note=f"Testing user: {user.telegram_id}",
                    data_limit_gb=50,  # 50GB for testing
                    expire_days=days   # Testing period
                )
                
                vpn_config = VPNConfig(
                    user_id=user.id,
                    marzban_user_id=marzban_username,
                    config_data=marzban_user.links[0] if marzban_user.links else None,
                    is_active=True
                )
                async_session.add(vpn_config)
        
    except Exception as e:
        logger.error(f"Error ensuring VPN config for testing user {user.telegram_id}: {e}")


async def activate_trial_subscription(callback: CallbackQuery, user: User, session: AsyncSession, days: int):
    """Activate trial subscription for user"""
    logger.info(f"=== STARTING TRIAL ACTIVATION for user {user.telegram_id} ===")
    try:
        from database.models import VPNConfig
        
        # Mark trial as used
        logger.info(f"Marking trial as used for user {user.telegram_id}")
        user.trial_used = True
        
        # Check if user already has active subscription
        result = await session.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user.id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                )
            )
            .order_by(Subscription.created_at.desc())
        )
        current_subscription = result.scalar_one_or_none()
        
        now = datetime.now()
        if current_subscription and current_subscription.end_date > now:
            await callback.message.edit_text(
                "❌ **У вас уже есть активная подписка**\n\n"
                "Пробный период можно активировать только при отсутствии активной подписки.",
                reply_markup=get_back_button("payment"),
                parse_mode="Markdown"
            )
            await callback.answer("У вас уже есть активная подписка")
            return
        
        # Deactivate old subscriptions
        if current_subscription:
            current_subscription.status = SubscriptionStatus.EXPIRED
        
        # Get trial plan ID from database
        logger.info(f"Looking for trial plan in database...")
        result = await session.execute(
            select(PricingPlan).where(PricingPlan.name == "Пробный период")
        )
        trial_plan = result.scalar_one_or_none()
        
        if not trial_plan:
            logger.error("Trial plan not found in database")
            await callback.answer("❌ План пробного периода не найден", show_alert=True)
            return
        logger.info(f"Found trial plan: {trial_plan.name} (ID: {trial_plan.id})")
        
        # Create new trial subscription
        logger.info(f"Creating new trial subscription for {days} days")
        trial_subscription = Subscription(
            user_id=user.id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.TRIAL,
            start_date=now,
            end_date=now + timedelta(days=days),
            auto_renew=False
        )
        session.add(trial_subscription)
        await session.flush()  # Get subscription ID
        logger.info(f"Trial subscription created with ID: {trial_subscription.id}")
        
        # Create or activate VPN config
        logger.info(f"Checking for existing VPN config for user {user.id}")
        result = await session.execute(
            select(VPNConfig).where(VPNConfig.user_id == user.id)
        )
        vpn_config = result.scalar_one_or_none()
        
        if vpn_config:
            # Check if existing config has valid data
            logger.info(f"Found existing VPN config {vpn_config.id}")
            if vpn_config.config_data:
                logger.info(f"Existing config has data, reactivating...")
                vpn_config.is_active = True
            else:
                logger.info(f"Existing config has no data, deleting and creating new one...")
                await session.delete(vpn_config)
                await session.flush()
                vpn_config = None  # Set to None to trigger creation below
        
        if not vpn_config:
            # Try to create new VPN config, but don't fail if Marzban is unavailable
            logger.info(f"No VPN config found, creating new one via Marzban...")
            try:
                from services.marzban import marzban_client, generate_unique_username
                marzban_username = generate_unique_username(user.telegram_id)
                logger.info(f"Generated Marzban username: {marzban_username}")
                
                # Try to create user, handle 409 if exists
                async with marzban_client as client:
                    try:
                        logger.info(f"Attempting to create Marzban user {marzban_username}...")
                        marzban_user = await client.create_user(
                            username=marzban_username,
                            note=f"Trial user: {user.telegram_id}",
                            data_limit_gb=10,  # 10GB for trial
                            expire_days=days   # Trial period in days
                        )
                        logger.info(f"Marzban user created successfully: {marzban_user.username}")
                        logger.info(f"Marzban user links: {marzban_user.links if hasattr(marzban_user, 'links') else 'No links attribute'}")
                        logger.info(f"Marzban user data: {marzban_user}")
                        logger.info(f"DEBUG: About to check excluded_inbounds logic...")
                        
                        # Debug excluded_inbounds
                        logger.info(f"Checking excluded_inbounds: {getattr(marzban_user, 'excluded_inbounds', 'No attribute')}")
                        if hasattr(marzban_user, 'excluded_inbounds'):
                            logger.info(f"excluded_inbounds type: {type(marzban_user.excluded_inbounds)}")
                            logger.info(f"excluded_inbounds content: {marzban_user.excluded_inbounds}")
                            if marzban_user.excluded_inbounds:
                                logger.info(f"excluded_inbounds is truthy")
                                if 'vless' in marzban_user.excluded_inbounds:
                                    logger.info(f"'vless' key found: {marzban_user.excluded_inbounds['vless']}")
                                    if 'VLESS TCP REALITY' in marzban_user.excluded_inbounds['vless']:
                                        logger.info(f"'VLESS TCP REALITY' found in vless exclusions")
                        
                        # If user has excluded_inbounds, delete and recreate without exclusions
                        if (hasattr(marzban_user, 'excluded_inbounds') and 
                            marzban_user.excluded_inbounds and 
                            'vless' in marzban_user.excluded_inbounds and 
                            'VLESS TCP REALITY' in marzban_user.excluded_inbounds['vless']):
                            
                            logger.info(f"User is excluded from VLESS TCP REALITY, recreating user...")
                            
                            # Delete user
                            delete_success = await client.delete_user(marzban_username)
                            logger.info(f"Delete user result: {delete_success}")
                            
                            if delete_success:
                                # Recreate without excluded_inbounds
                                logger.info(f"Recreating user without excluded_inbounds...")
                                marzban_user = await client.create_user(
                                    username=marzban_username,
                                    data_limit_gb=10,
                                    expire_days=days
                                )
                                logger.info(f"Recreated user data: {marzban_user}")
                        
                        # If still no links, try update approach
                        if not (hasattr(marzban_user, 'links') and marzban_user.links):
                            logger.info(f"User still has no links, trying to update with empty excluded_inbounds...")
                            try:
                                updated_user = await client.update_user(
                                    username=marzban_username,
                                    expire_days=days,
                                    data_limit_gb=10,
                                    status=marzban_user.status,
                                    excluded_inbounds={}
                                )
                                logger.info(f"Updated user links: {updated_user.links if hasattr(updated_user, 'links') else 'No links'}")
                                if hasattr(updated_user, 'links') and updated_user.links:
                                    marzban_user = updated_user
                                    logger.info(f"Successfully fixed user links!")
                            except Exception as update_error:
                                logger.error(f"Failed to update user: {update_error}")
                    except Exception as create_error:
                        if "409" in str(create_error):
                            logger.info(f"User {marzban_username} already exists (409), deleting and recreating...")
                            try:
                                # Delete existing user
                                delete_success = await client.delete_user(marzban_username)
                                if delete_success:
                                    logger.info(f"Successfully deleted existing user {marzban_username}")
                                    # Try to create again
                                    marzban_user = await client.create_user(
                                        username=marzban_username,
                                        note=f"Trial user: {user.telegram_id}",
                                        data_limit_gb=10,  # 10GB for trial
                                        expire_days=days   # Trial period in days
                                    )
                                    logger.info(f"Successfully recreated Marzban user: {marzban_user.username}")
                                    # Wait a moment for Marzban to generate config links
                                    import asyncio
                                    await asyncio.sleep(2)
                                    logger.info(f"Waited 2 seconds for Marzban to generate configs")
                                    # Fetch user again to get updated links
                                    marzban_user = await client.get_user(marzban_username)
                                    logger.info(f"Refetched user, links: {marzban_user.links if (hasattr(marzban_user, 'links') and marzban_user) else 'None'}")
                                else:
                                    logger.error(f"Failed to delete existing user {marzban_username}")
                                    raise create_error
                            except Exception as delete_error:
                                logger.error(f"Error during delete and recreate: {delete_error}")
                                raise create_error
                        else:
                            logger.error(f"Failed to create Marzban user: {create_error}")
                            raise create_error
                    
                    # Get config data from user links or fetch it separately
                    config_data = None
                    if hasattr(marzban_user, 'links') and marzban_user.links:
                        config_data = marzban_user.links[0]
                        logger.info(f"Got config from user links: {config_data[:100] if config_data else 'None'}...")
                    else:
                        logger.info("No links in user object, trying to fetch config separately...")
                        try:
                            config_data = await client.get_user_config(marzban_username)
                            logger.info(f"Got config from get_user_config: {config_data[:100] if config_data else 'None'}...")
                        except Exception as config_error:
                            logger.error(f"Failed to get config separately: {config_error}")
                    
                    vpn_config = VPNConfig(
                        user_id=user.id,
                        marzban_user_id=marzban_username,
                        config_data=config_data,
                        is_active=True if config_data else False
                    )
                    session.add(vpn_config)
                    logger.info(f"VPN config created in database for user {user.id}")
            except Exception as marzban_error:
                logger.error(f"MARZBAN ERROR: Could not create VPN config via Marzban: {marzban_error}")
                logger.error(f"Marzban error details: {str(marzban_error)}")
                import traceback
                logger.error(f"Marzban traceback: {traceback.format_exc()}")
                
                # Create placeholder config that user can get later
                logger.info(f"Creating placeholder VPN config for user {user.id}")
                vpn_config = VPNConfig(
                    user_id=user.id,
                    marzban_user_id=f"trial_{user.telegram_id}",
                    config_data=None,  # Will be generated later when Marzban is available
                    is_active=False  # Will be activated when config is ready
                )
                session.add(vpn_config)
        
        logger.info(f"Committing changes to database...")
        await session.commit()
        logger.info(f"Changes committed successfully")
        
        # Check if VPN config was successfully created
        if vpn_config and vpn_config.is_active and vpn_config.config_data:
            config_message = f"🔑 Получите конфигурацию: /config\n\n"
            logger.info(f"VPN config ready for user {user.telegram_id}")
        else:
            config_message = f"⚠️ VPN конфигурация готовится. Попробуйте получить её позже: /config\n\n"
            logger.info(f"VPN config not ready for user {user.telegram_id}, will be created later")
        
        await callback.message.edit_text(
            f"🎉 **Пробный период активирован!**\n\n"
            f"✅ Подписка: {days} дней\n"
            f"📅 Действует до: {trial_subscription.end_date.strftime('%d.%m.%Y')}\n"
            f"{config_message}"
            f"После окончания пробного периода вы можете оформить полную подписку.",
            reply_markup=get_back_button("main_menu"),
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Пробный период активирован!")
        logger.info(f"=== TRIAL ACTIVATION COMPLETED for user {user.telegram_id} ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR activating trial subscription: {e}")
        logger.error(f"Error details: {str(e)}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        await callback.answer("❌ Ошибка активации пробного периода", show_alert=True)


def create_dynamic_payment_keyboard(plans):
    """Create dynamic payment keyboard based on available plans"""
    builder = InlineKeyboardBuilder()
    
    # Add buttons for each plan
    for plan_name in plans.keys():
        if plan_name == "Пробный период":
            builder.row(
                InlineKeyboardButton(text="🆓 Пробный период", callback_data="plan_trial")
            )
        elif plan_name == "Месячная подписка":
            builder.row(
                InlineKeyboardButton(text="📅 1 месяц", callback_data="plan_monthly")
            )
        elif plan_name == "Квартальная подписка":
            builder.row(
                InlineKeyboardButton(text="📅 3 месяца (-10%)", callback_data="plan_quarterly")
            )
        elif plan_name == "Годовая подписка":
            builder.row(
                InlineKeyboardButton(text="📅 12 месяцев (-20%)", callback_data="plan_yearly")
            )
        else:
            # Generic fallback for any other plans
            builder.row(
                InlineKeyboardButton(text=f"📅 {plan_name}", callback_data=f"plan_{plan_name}")
            )
    
    # Add promo code and back buttons
    builder.row(
        InlineKeyboardButton(text="🎁 У меня есть промокод", callback_data="enter_promo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """States for admin operations"""
    
    # User management
    searching_user = State()
    editing_user = State()
    blocking_user = State()
    entering_block_reason = State()
    
    # Broadcast management
    creating_broadcast = State()
    entering_broadcast_title = State()
    entering_broadcast_content = State()
    selecting_broadcast_audience = State()
    confirming_broadcast = State()
    
    # Statistics and reports
    generating_report = State()
    selecting_report_period = State()
    
    # System settings
    editing_setting = State()
    entering_setting_value = State()
    
    # Promo codes
    creating_promo = State()
    entering_promo_code = State()
    entering_promo_value = State()
    entering_promo_description = State()
    
    # Subscription management  
    managing_subscription = State()
    extending_user_subscription = State()
    entering_extension_period = State()
    
    # Payment management
    reviewing_payment = State()
    processing_refund = State()
    entering_refund_details = State()
    
    # VPN config management
    regenerating_config = State()
    troubleshooting_config = State()
    
    # Pricing plans
    creating_pricing_plan = State()
    editing_pricing_plan = State()
    entering_plan_details = State()
    
    # FAQ management
    creating_faq = State()
    editing_faq = State()
    entering_faq_question = State()
    entering_faq_answer = State()
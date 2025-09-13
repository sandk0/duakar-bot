from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """States for payment process"""
    
    # Plan selection
    selecting_plan = State()
    
    # Promo code
    entering_promo = State()
    
    # Payment method selection
    selecting_payment_method = State()
    
    # Payment processing
    processing_payment = State()
    waiting_payment = State()
    
    # Payment confirmation
    confirming_payment = State()
    
    # Subscription extension
    extending_subscription = State()
    entering_extension_days = State()
    
    # Refund process
    requesting_refund = State()
    entering_refund_reason = State()
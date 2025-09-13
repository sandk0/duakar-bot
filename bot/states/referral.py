from aiogram.fsm.state import State, StatesGroup


class ReferralStates(StatesGroup):
    """States for referral system"""
    
    # Referral management
    viewing_referrals = State()
    inviting_friend = State()
    
    # Bonus management
    viewing_bonuses = State()
    using_bonus = State()
    
    # Referral link sharing
    sharing_referral_link = State()
    customizing_referral_message = State()
    
    # Referral statistics
    viewing_referral_stats = State()
    
    # Bonus redemption
    redeeming_bonus = State()
    selecting_bonus_type = State()
    confirming_bonus_use = State()
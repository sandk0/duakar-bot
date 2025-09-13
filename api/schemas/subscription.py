from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from .common import MetadataSchema


class SubscriptionBaseSchema(BaseModel):
    """Base subscription schema"""
    plan_type: str = Field(..., max_length=50, description="Subscription plan type")
    status: str = Field("active", description="Subscription status", regex="^(active|expired|cancelled|suspended)$")
    auto_renewal: bool = Field(True, description="Whether auto-renewal is enabled")
    is_trial: bool = Field(False, description="Whether this is a trial subscription")


class SubscriptionCreateSchema(SubscriptionBaseSchema):
    """Schema for creating subscription"""
    user_id: int = Field(..., gt=0, description="User ID")
    start_date: Optional[datetime] = Field(None, description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        start_date = values.get('start_date', datetime.utcnow())
        if v and v <= start_date:
            raise ValueError('End date must be after start date')
        return v


class SubscriptionUpdateSchema(BaseModel):
    """Schema for updating subscription"""
    plan_type: Optional[str] = Field(None, max_length=50, description="Subscription plan type")
    status: Optional[str] = Field(None, description="Subscription status", regex="^(active|expired|cancelled|suspended)$")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    auto_renewal: Optional[bool] = Field(None, description="Whether auto-renewal is enabled")


class SubscriptionSchema(SubscriptionBaseSchema, MetadataSchema):
    """Complete subscription schema"""
    id: int = Field(..., description="Subscription ID")
    user_id: int = Field(..., description="User ID")
    start_date: Optional[datetime] = Field(None, description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    
    # Calculated fields
    days_remaining: Optional[int] = Field(None, description="Days remaining in subscription")
    is_expired: Optional[bool] = Field(None, description="Whether subscription is expired")
    
    class Config:
        from_attributes = True


class SubscriptionWithUserSchema(SubscriptionSchema):
    """Subscription schema with user information"""
    user: Optional[dict] = Field(None, description="User information")


class SubscriptionWithDetailsSchema(SubscriptionSchema):
    """Subscription schema with detailed information"""
    user: Optional[dict] = Field(None, description="User information")
    vpn_config: Optional[dict] = Field(None, description="VPN configuration")
    payments: List[dict] = Field(default=[], description="Payment history")
    usage_stats: Optional[dict] = Field(None, description="Usage statistics")


class SubscriptionStatsSchema(BaseModel):
    """Subscription statistics schema"""
    total_subscriptions: int = Field(..., ge=0, description="Total subscriptions")
    active_subscriptions: int = Field(..., ge=0, description="Active subscriptions")
    expired_subscriptions: int = Field(..., ge=0, description="Expired subscriptions")
    trial_subscriptions: int = Field(..., ge=0, description="Trial subscriptions")
    paid_subscriptions: int = Field(..., ge=0, description="Paid subscriptions")
    cancelled_subscriptions: int = Field(..., ge=0, description="Cancelled subscriptions")
    renewal_rate: float = Field(..., ge=0, le=100, description="Renewal rate percentage")
    churn_rate: float = Field(..., ge=0, le=100, description="Churn rate percentage")
    average_lifetime: Optional[float] = Field(None, description="Average subscription lifetime in days")


class SubscriptionExtensionSchema(BaseModel):
    """Schema for extending subscription"""
    days: int = Field(..., gt=0, le=365, description="Number of days to extend")
    reason: Optional[str] = Field(None, description="Reason for extension")
    free_extension: bool = Field(False, description="Whether this is a free extension")
    
    @validator('days')
    def validate_days(cls, v):
        if v <= 0 or v > 365:
            raise ValueError('Extension days must be between 1 and 365')
        return v


class SubscriptionFilterSchema(BaseModel):
    """Schema for filtering subscriptions"""
    status: Optional[str] = Field(None, regex="^(active|expired|cancelled|suspended)$")
    plan_type: Optional[str] = Field(None)
    is_trial: Optional[bool] = Field(None)
    user_id: Optional[int] = Field(None, gt=0)
    expires_in_days: Optional[int] = Field(None, ge=0, le=365, description="Expires within X days")
    auto_renewal: Optional[bool] = Field(None)


class BulkSubscriptionActionSchema(BaseModel):
    """Schema for bulk subscription actions"""
    subscription_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of subscription IDs")
    action: str = Field(..., regex="^(cancel|suspend|activate|extend)$", description="Action to perform")
    parameters: Optional[dict] = Field(None, description="Action parameters (e.g., extension days)")
    reason: Optional[str] = Field(None, description="Reason for the action")


class SubscriptionRenewalSchema(BaseModel):
    """Schema for subscription renewal"""
    plan_type: Optional[str] = Field(None, description="New plan type")
    payment_method: Optional[str] = Field(None, description="Payment method")
    promo_code: Optional[str] = Field(None, description="Promo code to apply")
    auto_renewal: bool = Field(True, description="Enable auto-renewal")
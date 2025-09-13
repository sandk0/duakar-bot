from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from .common import MetadataSchema


class UserBaseSchema(BaseModel):
    """Base user schema"""
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, max_length=255, description="Telegram username")
    first_name: Optional[str] = Field(None, max_length=255, description="First name")
    last_name: Optional[str] = Field(None, max_length=255, description="Last name")
    language_code: Optional[str] = Field(None, max_length=10, description="Language code")


class UserCreateSchema(UserBaseSchema):
    """Schema for creating a new user"""
    referrer_id: Optional[int] = Field(None, description="Referrer user ID")
    
    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v <= 0:
            raise ValueError('Telegram ID must be positive')
        return v


class UserUpdateSchema(BaseModel):
    """Schema for updating user"""
    username: Optional[str] = Field(None, max_length=255, description="Telegram username")
    first_name: Optional[str] = Field(None, max_length=255, description="First name")
    last_name: Optional[str] = Field(None, max_length=255, description="Last name")
    language_code: Optional[str] = Field(None, max_length=10, description="Language code")
    is_blocked: Optional[bool] = Field(None, description="Whether user is blocked")
    block_reason: Optional[str] = Field(None, description="Reason for blocking")
    is_admin: Optional[bool] = Field(None, description="Whether user is admin")


class UserSchema(UserBaseSchema, MetadataSchema):
    """Complete user schema"""
    id: int = Field(..., description="User ID")
    referrer_id: Optional[int] = Field(None, description="Referrer user ID")
    is_blocked: bool = Field(False, description="Whether user is blocked")
    block_reason: Optional[str] = Field(None, description="Reason for blocking")
    is_admin: bool = Field(False, description="Whether user is admin")
    
    # Relationships
    subscription_count: Optional[int] = Field(None, description="Number of subscriptions")
    payment_count: Optional[int] = Field(None, description="Number of payments")
    referral_count: Optional[int] = Field(None, description="Number of referrals")
    
    class Config:
        from_attributes = True


class UserStatsSchema(BaseModel):
    """User statistics schema"""
    total_users: int = Field(..., ge=0, description="Total number of users")
    active_users: int = Field(..., ge=0, description="Number of active users")
    blocked_users: int = Field(..., ge=0, description="Number of blocked users")
    admin_users: int = Field(..., ge=0, description="Number of admin users")
    new_users_today: int = Field(..., ge=0, description="New users today")
    new_users_week: int = Field(..., ge=0, description="New users this week")
    new_users_month: int = Field(..., ge=0, description="New users this month")


class UserWithReferralsSchema(UserSchema):
    """User schema with referral information"""
    referrals: List[UserSchema] = Field(default=[], description="List of referred users")
    referral_stats: Optional[dict] = Field(None, description="Referral statistics")


class UserBlockSchema(BaseModel):
    """Schema for blocking/unblocking user"""
    is_blocked: bool = Field(..., description="Whether to block or unblock user")
    block_reason: Optional[str] = Field(None, description="Reason for blocking")
    
    @validator('block_reason')
    def validate_block_reason(cls, v, values):
        if values.get('is_blocked') and not v:
            raise ValueError('Block reason is required when blocking user')
        return v


class UserSearchSchema(BaseModel):
    """Schema for user search"""
    query: str = Field(..., min_length=1, max_length=255, description="Search query")
    search_by: Optional[str] = Field("all", description="Search field", regex="^(all|username|telegram_id|name)$")
    include_blocked: Optional[bool] = Field(False, description="Include blocked users in search")


class BulkUserActionSchema(BaseModel):
    """Schema for bulk user actions"""
    user_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of user IDs")
    action: str = Field(..., description="Action to perform", regex="^(block|unblock|delete|make_admin|remove_admin)$")
    reason: Optional[str] = Field(None, description="Reason for the action")
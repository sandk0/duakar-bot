from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class AdminUserSchema(BaseModel):
    """Admin user information schema"""
    id: int = Field(..., description="Admin user ID")
    telegram_id: int = Field(..., description="Telegram ID")
    username: Optional[str] = Field(None, description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_admin: bool = Field(True, description="Admin status")
    permissions: List[str] = Field(default=[], description="Admin permissions")
    created_at: datetime = Field(..., description="Admin creation date")
    last_active: Optional[datetime] = Field(None, description="Last activity date")


class AdminStatsSchema(BaseModel):
    """Admin dashboard statistics"""
    # User statistics
    total_users: int = Field(..., ge=0, description="Total users")
    active_users: int = Field(..., ge=0, description="Active users") 
    new_users_today: int = Field(..., ge=0, description="New users today")
    new_users_week: int = Field(..., ge=0, description="New users this week")
    
    # Subscription statistics  
    total_subscriptions: int = Field(..., ge=0, description="Total subscriptions")
    active_subscriptions: int = Field(..., ge=0, description="Active subscriptions")
    expired_subscriptions: int = Field(..., ge=0, description="Expired subscriptions")
    trial_subscriptions: int = Field(..., ge=0, description="Trial subscriptions")
    
    # Payment statistics
    total_payments: int = Field(..., ge=0, description="Total payments")
    successful_payments: int = Field(..., ge=0, description="Successful payments")
    failed_payments: int = Field(..., ge=0, description="Failed payments")
    total_revenue: Decimal = Field(..., ge=0, description="Total revenue")
    revenue_today: Decimal = Field(..., ge=0, description="Revenue today")
    revenue_month: Decimal = Field(..., ge=0, description="Revenue this month")
    
    # VPN statistics
    active_vpn_configs: int = Field(..., ge=0, description="Active VPN configs")
    total_data_used: Optional[int] = Field(None, description="Total data used in bytes")
    
    # System statistics
    system_uptime: float = Field(..., ge=0, description="System uptime in hours")
    database_size: Optional[int] = Field(None, description="Database size in bytes")
    error_rate: float = Field(..., ge=0, le=100, description="Error rate percentage")


class SystemHealthSchema(BaseModel):
    """System health status schema"""
    overall_status: str = Field(..., description="Overall system status")
    database_status: str = Field(..., description="Database status")
    redis_status: str = Field(..., description="Redis status")
    marzban_status: str = Field(..., description="Marzban API status")
    bot_status: str = Field(..., description="Telegram bot status")
    celery_status: str = Field(..., description="Celery worker status")
    last_check: datetime = Field(..., description="Last health check time")
    uptime: float = Field(..., description="System uptime in seconds")


class BroadcastMessageSchema(BaseModel):
    """Broadcast message schema"""
    title: Optional[str] = Field(None, max_length=255, description="Message title")
    content: str = Field(..., min_length=1, max_length=4096, description="Message content")
    target_audience: str = Field("all", description="Target audience", regex="^(all|active|trial|premium|inactive)$")
    send_immediately: bool = Field(True, description="Send immediately or schedule")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule send time")
    
    @validator('scheduled_at')
    def validate_scheduled_at(cls, v, values):
        if not values.get('send_immediately') and not v:
            raise ValueError('Scheduled time is required when not sending immediately')
        if v and v <= datetime.utcnow():
            raise ValueError('Scheduled time must be in the future')
        return v


class BroadcastStatusSchema(BaseModel):
    """Broadcast status schema"""
    id: int = Field(..., description="Broadcast ID")
    title: Optional[str] = Field(None, description="Message title")
    status: str = Field(..., description="Broadcast status")
    target_audience: str = Field(..., description="Target audience")
    total_recipients: int = Field(..., ge=0, description="Total recipients")
    sent_count: int = Field(..., ge=0, description="Messages sent")
    failed_count: int = Field(..., ge=0, description="Failed sends")
    created_at: datetime = Field(..., description="Creation time")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


class AdminActionLogSchema(BaseModel):
    """Admin action log schema"""
    id: int = Field(..., description="Log entry ID")
    admin_id: int = Field(..., description="Admin user ID")
    action_type: str = Field(..., description="Action type")
    target_type: Optional[str] = Field(None, description="Target object type")
    target_id: Optional[int] = Field(None, description="Target object ID")
    description: str = Field(..., description="Action description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Action timestamp")


class PromoCodeCreateSchema(BaseModel):
    """Schema for creating promo code"""
    code: str = Field(..., min_length=3, max_length=50, description="Promo code")
    type: str = Field(..., regex="^(discount|bonus_days|fixed_amount)$", description="Promo code type")
    value: Decimal = Field(..., gt=0, description="Promo code value")
    max_uses: Optional[int] = Field(None, gt=0, description="Maximum number of uses")
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_until: Optional[datetime] = Field(None, description="Valid until date")
    description: Optional[str] = Field(None, description="Promo code description")
    
    @validator('code')
    def validate_code(cls, v):
        return v.upper().strip()
    
    @validator('valid_until')
    def validate_valid_until(cls, v, values):
        valid_from = values.get('valid_from')
        if v and valid_from and v <= valid_from:
            raise ValueError('Valid until date must be after valid from date')
        return v


class SettingUpdateSchema(BaseModel):
    """Schema for updating system setting"""
    key: str = Field(..., min_length=1, max_length=100, description="Setting key")
    value: str = Field(..., description="Setting value")
    description: Optional[str] = Field(None, description="Setting description")


class TestingModeToggleSchema(BaseModel):
    """Schema for toggling testing mode"""
    testing_mode: bool = Field(..., description="Enable/disable testing mode")
    reason: Optional[str] = Field(None, description="Reason for change")


class AdminPermissionSchema(BaseModel):
    """Admin permission schema"""
    permission: str = Field(..., description="Permission name")
    description: str = Field(..., description="Permission description")
    category: str = Field(..., description="Permission category")


class BulkAdminActionSchema(BaseModel):
    """Schema for bulk admin actions"""
    target_type: str = Field(..., regex="^(users|subscriptions|payments)$", description="Target object type")
    target_ids: List[int] = Field(..., min_items=1, max_items=100, description="Target object IDs")
    action: str = Field(..., description="Action to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for action")
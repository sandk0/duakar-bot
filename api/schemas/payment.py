from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .common import MetadataSchema


class PaymentBaseSchema(BaseModel):
    """Base payment schema"""
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2, description="Payment amount")
    currency: str = Field("RUB", max_length=10, description="Payment currency")
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method")
    payment_system: str = Field(..., max_length=50, description="Payment system (yookassa, wata)")
    description: Optional[str] = Field(None, description="Payment description")


class PaymentCreateSchema(PaymentBaseSchema):
    """Schema for creating payment"""
    user_id: int = Field(..., gt=0, description="User ID")
    subscription_id: Optional[int] = Field(None, gt=0, description="Subscription ID")
    external_payment_id: Optional[str] = Field(None, max_length=255, description="External payment system ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional payment metadata")
    
    @validator('payment_system')
    def validate_payment_system(cls, v):
        allowed_systems = ['yookassa', 'wata', 'test']
        if v not in allowed_systems:
            raise ValueError(f'Payment system must be one of: {allowed_systems}')
        return v


class PaymentUpdateSchema(BaseModel):
    """Schema for updating payment"""
    status: Optional[str] = Field(None, regex="^(pending|processing|completed|failed|cancelled|refunded)$")
    external_payment_id: Optional[str] = Field(None, max_length=255)
    payment_method: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(None)
    description: Optional[str] = Field(None)


class PaymentSchema(PaymentBaseSchema, MetadataSchema):
    """Complete payment schema"""
    id: int = Field(..., description="Payment ID")
    user_id: int = Field(..., description="User ID")
    subscription_id: Optional[int] = Field(None, description="Subscription ID")
    status: str = Field(..., description="Payment status")
    external_payment_id: Optional[str] = Field(None, description="External payment system ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional payment metadata")
    
    class Config:
        from_attributes = True


class PaymentWithDetailsSchema(PaymentSchema):
    """Payment schema with detailed information"""
    user: Optional[dict] = Field(None, description="User information")
    subscription: Optional[dict] = Field(None, description="Subscription information")


class PaymentStatsSchema(BaseModel):
    """Payment statistics schema"""
    total_payments: int = Field(..., ge=0, description="Total number of payments")
    successful_payments: int = Field(..., ge=0, description="Number of successful payments")
    failed_payments: int = Field(..., ge=0, description="Number of failed payments")
    pending_payments: int = Field(..., ge=0, description="Number of pending payments")
    refunded_payments: int = Field(..., ge=0, description="Number of refunded payments")
    total_revenue: Decimal = Field(..., ge=0, description="Total revenue")
    revenue_today: Decimal = Field(..., ge=0, description="Revenue today")
    revenue_month: Decimal = Field(..., ge=0, description="Revenue this month")
    average_payment_amount: Optional[Decimal] = Field(None, description="Average payment amount")
    success_rate: float = Field(..., ge=0, le=100, description="Payment success rate percentage")


class PaymentFilterSchema(BaseModel):
    """Schema for filtering payments"""
    status: Optional[str] = Field(None, regex="^(pending|processing|completed|failed|cancelled|refunded)$")
    payment_system: Optional[str] = Field(None)
    payment_method: Optional[str] = Field(None)
    user_id: Optional[int] = Field(None, gt=0)
    subscription_id: Optional[int] = Field(None, gt=0)
    amount_from: Optional[Decimal] = Field(None, ge=0)
    amount_to: Optional[Decimal] = Field(None, ge=0)
    date_from: Optional[datetime] = Field(None)
    date_to: Optional[datetime] = Field(None)


class RefundRequestSchema(BaseModel):
    """Schema for refund request"""
    payment_id: int = Field(..., gt=0, description="Payment ID to refund")
    amount: Optional[Decimal] = Field(None, gt=0, description="Refund amount (partial refund)")
    reason: str = Field(..., min_length=3, max_length=500, description="Refund reason")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Refund amount must be positive')
        return v


class RefundSchema(BaseModel):
    """Refund information schema"""
    id: int = Field(..., description="Refund ID")
    payment_id: int = Field(..., description="Original payment ID")
    amount: Decimal = Field(..., description="Refund amount")
    reason: str = Field(..., description="Refund reason")
    status: str = Field(..., description="Refund status")
    external_refund_id: Optional[str] = Field(None, description="External refund ID")
    created_at: datetime = Field(..., description="Refund creation date")
    processed_at: Optional[datetime] = Field(None, description="Refund processing date")


class PaymentMethodSchema(BaseModel):
    """Payment method information schema"""
    type: str = Field(..., description="Payment method type")
    title: str = Field(..., description="Payment method title")
    description: Optional[str] = Field(None, description="Payment method description")
    fee: Optional[Decimal] = Field(None, description="Payment method fee")
    fee_type: Optional[str] = Field(None, description="Fee type (fixed, percentage)")
    is_available: bool = Field(True, description="Whether payment method is available")
    min_amount: Optional[Decimal] = Field(None, description="Minimum payment amount")
    max_amount: Optional[Decimal] = Field(None, description="Maximum payment amount")


class PaymentWebhookSchema(BaseModel):
    """Payment webhook data schema"""
    event_type: str = Field(..., description="Webhook event type")
    payment_id: str = Field(..., description="External payment ID")
    status: str = Field(..., description="Payment status")
    amount: Optional[Decimal] = Field(None, description="Payment amount")
    currency: Optional[str] = Field(None, description="Payment currency")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional webhook data")
    signature: Optional[str] = Field(None, description="Webhook signature for verification")


class BulkPaymentActionSchema(BaseModel):
    """Schema for bulk payment actions"""
    payment_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of payment IDs")
    action: str = Field(..., regex="^(refund|cancel|retry)$", description="Action to perform")
    parameters: Optional[dict] = Field(None, description="Action parameters")
    reason: Optional[str] = Field(None, description="Reason for the action")
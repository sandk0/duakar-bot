from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
from decimal import Decimal


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success" 
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CARD = "card"
    SBP = "sbp"
    YOOMONEY = "yoomoney"
    QIWI = "qiwi"


class PaymentRequest(BaseModel):
    amount: Decimal
    currency: str = "RUB"
    description: str
    order_id: str
    return_url: Optional[str] = None
    webhook_url: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class PaymentCallback(BaseModel):
    payment_id: str
    order_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Dict[str, Any]


class BasePaymentProvider(ABC):
    """Base class for payment providers"""
    
    def __init__(self, api_key: str, secret_key: str, webhook_secret: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
    
    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create a new payment"""
        pass
    
    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status by ID"""
        pass
    
    @abstractmethod
    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel payment"""
        pass
    
    @abstractmethod
    def verify_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify webhook signature"""
        pass
    
    @abstractmethod
    def parse_webhook(self, data: Dict[str, Any]) -> PaymentCallback:
        """Parse webhook data"""
        pass
    
    @abstractmethod
    def get_supported_methods(self) -> list[PaymentMethod]:
        """Get list of supported payment methods"""
        pass
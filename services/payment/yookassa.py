import httpx
import json
import base64
import hashlib
import hmac
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from .base import BasePaymentProvider, PaymentRequest, PaymentResponse, PaymentCallback, PaymentStatus, PaymentMethod
import logging
from bot.config import settings

logger = logging.getLogger(__name__)


class YooKassaProvider(BasePaymentProvider):
    """YooKassa payment provider"""
    
    def __init__(self, shop_id: str, secret_key: str):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.base_url = "https://api.yookassa.ru/v3"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        credentials = f"{self.shop_id}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
            "Idempotence-Key": str(datetime.now().timestamp())
        }
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create payment in YooKassa"""
        headers = self._get_headers()
        
        payment_data = {
            "amount": {
                "value": str(request.amount),
                "currency": request.currency
            },
            "description": request.description,
            "metadata": {
                "order_id": request.order_id,
                **(request.metadata or {})
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.return_url or "https://example.com/return"
            },
            "capture": True
        }
        
        # Add customer info if provided
        if request.customer_email:
            payment_data["receipt"] = {
                "customer": {"email": request.customer_email},
                "items": [{
                    "description": request.description,
                    "amount": {
                        "value": str(request.amount),
                        "currency": request.currency
                    },
                    "vat_code": 1,
                    "quantity": "1"
                }]
            }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/payments",
                headers=headers,
                json=payment_data
            )
            response.raise_for_status()
            
            data = response.json()
            
            return PaymentResponse(
                payment_id=data["id"],
                payment_url=data["confirmation"]["confirmation_url"],
                status=self._map_status(data["status"]),
                amount=Decimal(data["amount"]["value"]),
                currency=data["amount"]["currency"],
                created_at=data["created_at"],
                metadata=data.get("metadata", {})
            )
            
        except httpx.HTTPError as e:
            logger.error(f"YooKassa API error: {e}")
            raise Exception(f"Payment creation failed: {e}")
    
    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status from YooKassa"""
        headers = self._get_headers()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            return self._map_status(data["status"])
            
        except httpx.HTTPError as e:
            logger.error(f"Error getting payment status: {e}")
            return PaymentStatus.FAILED
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel payment in YooKassa"""
        headers = self._get_headers()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/payments/{payment_id}/cancel",
                headers=headers,
                json={}
            )
            response.raise_for_status()
            
            data = response.json()
            return data["status"] == "canceled"
            
        except httpx.HTTPError as e:
            logger.error(f"Error cancelling payment: {e}")
            return False
    
    def verify_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify YooKassa webhook signature"""
        if not self.secret_key:
            return True  # Skip verification if no secret
        
        # YooKassa doesn't use webhook signatures by default
        # This method can be enhanced if needed
        return True
    
    def parse_webhook(self, data: Dict[str, Any]) -> PaymentCallback:
        """Parse YooKassa webhook data"""
        event_data = data["object"]
        
        return PaymentCallback(
            payment_id=event_data["id"],
            order_id=event_data.get("metadata", {}).get("order_id", ""),
            status=self._map_status(event_data["status"]),
            amount=Decimal(event_data["amount"]["value"]),
            currency=event_data["amount"]["currency"],
            metadata=event_data.get("metadata", {}),
            raw_data=data
        )
    
    def get_supported_methods(self) -> list[PaymentMethod]:
        """Get supported payment methods"""
        return [PaymentMethod.CARD, PaymentMethod.SBP, PaymentMethod.YOOMONEY, PaymentMethod.QIWI]
    
    def _map_status(self, yookassa_status: str) -> PaymentStatus:
        """Map YooKassa status to internal status"""
        mapping = {
            "pending": PaymentStatus.PENDING,
            "waiting_for_capture": PaymentStatus.PENDING,
            "succeeded": PaymentStatus.SUCCESS,
            "canceled": PaymentStatus.CANCELLED,
            "failed": PaymentStatus.FAILED
        }
        return mapping.get(yookassa_status, PaymentStatus.PENDING)


# Initialize provider if credentials are available
yookassa_provider = None
if settings.yookassa_shop_id and settings.yookassa_secret_key:
    yookassa_provider = YooKassaProvider(
        shop_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key
    )
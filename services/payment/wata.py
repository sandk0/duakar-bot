import httpx
import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from .base import BasePaymentProvider, PaymentRequest, PaymentResponse, PaymentCallback, PaymentStatus, PaymentMethod
import logging
from bot.config import settings

logger = logging.getLogger(__name__)


class WataProvider(BasePaymentProvider):
    """Wata.pro payment provider"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.wata.pro/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate signature for request"""
        # Sort parameters
        sorted_params = sorted(data.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        # Create signature
        signature = hmac.new(
            self.secret_key.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create payment in Wata"""
        data = {
            "amount": str(request.amount),
            "currency": request.currency,
            "description": request.description,
            "order_id": request.order_id,
            "api_key": self.api_key,
            "return_url": request.return_url or "https://example.com/return",
            "webhook_url": request.webhook_url,
        }
        
        if request.customer_email:
            data["customer_email"] = request.customer_email
        
        if request.metadata:
            data.update({f"custom_{k}": str(v) for k, v in request.metadata.items()})
        
        # Generate signature
        data["signature"] = self._generate_signature(data)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/payments",
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("success"):
                raise Exception(f"Payment creation failed: {result.get('error', 'Unknown error')}")
            
            payment_data = result["data"]
            
            return PaymentResponse(
                payment_id=payment_data["payment_id"],
                payment_url=payment_data["payment_url"],
                status=self._map_status(payment_data.get("status", "pending")),
                amount=Decimal(payment_data["amount"]),
                currency=payment_data["currency"],
                created_at=payment_data.get("created_at", datetime.now().isoformat()),
                metadata={}
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Wata API error: {e}")
            raise Exception(f"Payment creation failed: {e}")
    
    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status from Wata"""
        data = {
            "payment_id": payment_id,
            "api_key": self.api_key
        }
        data["signature"] = self._generate_signature(data)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/payments/{payment_id}",
                params=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("success"):
                return PaymentStatus.FAILED
            
            return self._map_status(result["data"].get("status", "pending"))
            
        except httpx.HTTPError as e:
            logger.error(f"Error getting payment status: {e}")
            return PaymentStatus.FAILED
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel payment in Wata"""
        data = {
            "payment_id": payment_id,
            "api_key": self.api_key
        }
        data["signature"] = self._generate_signature(data)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/payments/{payment_id}/cancel",
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("success", False)
            
        except httpx.HTTPError as e:
            logger.error(f"Error cancelling payment: {e}")
            return False
    
    def verify_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify Wata webhook signature"""
        if not self.secret_key:
            return True
        
        signature = headers.get("X-Signature", "")
        expected_signature = hmac.new(
            self.secret_key.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def parse_webhook(self, data: Dict[str, Any]) -> PaymentCallback:
        """Parse Wata webhook data"""
        return PaymentCallback(
            payment_id=data["payment_id"],
            order_id=data.get("order_id", ""),
            status=self._map_status(data["status"]),
            amount=Decimal(data["amount"]),
            currency=data.get("currency", "RUB"),
            metadata={k.replace("custom_", ""): v for k, v in data.items() if k.startswith("custom_")},
            raw_data=data
        )
    
    def get_supported_methods(self) -> list[PaymentMethod]:
        """Get supported payment methods"""
        return [PaymentMethod.CARD, PaymentMethod.SBP, PaymentMethod.QIWI]
    
    def _map_status(self, wata_status: str) -> PaymentStatus:
        """Map Wata status to internal status"""
        mapping = {
            "pending": PaymentStatus.PENDING,
            "processing": PaymentStatus.PENDING,
            "paid": PaymentStatus.SUCCESS,
            "success": PaymentStatus.SUCCESS,
            "cancelled": PaymentStatus.CANCELLED,
            "canceled": PaymentStatus.CANCELLED,
            "failed": PaymentStatus.FAILED,
            "error": PaymentStatus.FAILED
        }
        return mapping.get(wata_status.lower(), PaymentStatus.PENDING)


# Initialize provider if credentials are available
wata_provider = None
if settings.wata_api_key and settings.wata_secret_key:
    wata_provider = WataProvider(
        api_key=settings.wata_api_key,
        secret_key=settings.wata_secret_key
    )
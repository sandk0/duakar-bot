from typing import Dict, List, Optional
from decimal import Decimal
from .base import BasePaymentProvider, PaymentRequest, PaymentResponse, PaymentCallback, PaymentMethod, PaymentStatus
from .yookassa import yookassa_provider
from .wata import wata_provider
import logging

logger = logging.getLogger(__name__)


class PaymentManager:
    """Payment manager to handle multiple payment providers"""
    
    def __init__(self):
        self.providers: Dict[str, BasePaymentProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available payment providers"""
        if yookassa_provider:
            self.providers["yookassa"] = yookassa_provider
            logger.info("YooKassa provider initialized")
        
        if wata_provider:
            self.providers["wata"] = wata_provider
            logger.info("Wata provider initialized")
        
        if not self.providers:
            logger.warning("No payment providers configured!")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available payment providers"""
        return list(self.providers.keys())
    
    def get_supported_methods(self, provider_name: Optional[str] = None) -> List[PaymentMethod]:
        """Get supported payment methods for provider or all providers"""
        if provider_name:
            provider = self.providers.get(provider_name)
            return provider.get_supported_methods() if provider else []
        
        # Return all unique methods from all providers
        all_methods = set()
        for provider in self.providers.values():
            all_methods.update(provider.get_supported_methods())
        
        return list(all_methods)
    
    def select_provider(self, method: PaymentMethod) -> Optional[str]:
        """Select best provider for payment method"""
        # Priority order for providers
        provider_priority = ["yookassa", "wata"]
        
        for provider_name in provider_priority:
            provider = self.providers.get(provider_name)
            if provider and method in provider.get_supported_methods():
                return provider_name
        
        return None
    
    async def create_payment(
        self,
        amount: Decimal,
        description: str,
        order_id: str,
        method: PaymentMethod = PaymentMethod.CARD,
        provider_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        return_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> tuple[PaymentResponse, str]:
        """Create payment using specified or best provider"""
        
        if not provider_name:
            provider_name = self.select_provider(method)
        
        if not provider_name:
            raise Exception(f"No provider available for payment method: {method}")
        
        provider = self.providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider not found: {provider_name}")
        
        request = PaymentRequest(
            amount=amount,
            description=description,
            order_id=order_id,
            return_url=return_url,
            webhook_url=webhook_url,
            customer_email=customer_email,
            metadata=metadata
        )
        
        try:
            response = await provider.create_payment(request)
            logger.info(f"Payment created: {response.payment_id} via {provider_name}")
            return response, provider_name
            
        except Exception as e:
            logger.error(f"Payment creation failed with {provider_name}: {e}")
            raise
    
    async def get_payment_status(self, payment_id: str, provider_name: str) -> PaymentStatus:
        """Get payment status from specific provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider not found: {provider_name}")
        
        return await provider.get_payment_status(payment_id)
    
    async def cancel_payment(self, payment_id: str, provider_name: str) -> bool:
        """Cancel payment using specific provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider not found: {provider_name}")
        
        return await provider.cancel_payment(payment_id)
    
    def verify_webhook(self, provider_name: str, headers: Dict[str, str], body: bytes) -> bool:
        """Verify webhook signature for specific provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            return False
        
        return provider.verify_webhook(headers, body)
    
    def parse_webhook(self, provider_name: str, data: Dict) -> PaymentCallback:
        """Parse webhook data for specific provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider not found: {provider_name}")
        
        return provider.parse_webhook(data)
    
    async def close(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()


# Global payment manager instance
payment_manager = PaymentManager()
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from database.models import User, Subscription, Payment, VPNConfig


class TestUserModel:
    def test_user_creation(self, sample_user_data):
        user = User(**sample_user_data)
        assert user.telegram_id == 123456789
        assert user.username == 'test_user'
        assert user.first_name == 'Test'
        assert user.is_blocked is False
        assert user.is_admin is False

    def test_user_repr(self, sample_user_data):
        user = User(**sample_user_data)
        assert repr(user) == f"<User(telegram_id={user.telegram_id}, username='test_user')>"


class TestSubscriptionModel:
    def test_subscription_creation(self, sample_subscription_data):
        subscription = Subscription(user_id=1, **sample_subscription_data)
        assert subscription.user_id == 1
        assert subscription.plan_type == 'monthly'
        assert subscription.status == 'active'
        assert subscription.is_trial is False
        assert subscription.auto_renewal is True

    def test_subscription_is_active(self):
        # Active subscription
        subscription = Subscription(
            user_id=1,
            status='active',
            end_date=datetime.utcnow() + timedelta(days=30)
        )
        assert subscription.is_active() is True

        # Expired subscription
        subscription.end_date = datetime.utcnow() - timedelta(days=1)
        assert subscription.is_active() is False

        # Cancelled subscription
        subscription.status = 'cancelled'
        subscription.end_date = datetime.utcnow() + timedelta(days=30)
        assert subscription.is_active() is False

    def test_subscription_days_remaining(self):
        subscription = Subscription(
            user_id=1,
            end_date=datetime.utcnow() + timedelta(days=15)
        )
        assert subscription.days_remaining() == 15

        # Past end date
        subscription.end_date = datetime.utcnow() - timedelta(days=5)
        assert subscription.days_remaining() == 0


class TestPaymentModel:
    def test_payment_creation(self, sample_payment_data):
        payment = Payment(user_id=1, **sample_payment_data)
        assert payment.user_id == 1
        assert payment.amount == Decimal('500.00')
        assert payment.currency == 'RUB'
        assert payment.payment_method == 'card'
        assert payment.payment_system == 'yookassa'
        assert payment.status == 'pending'

    def test_payment_is_successful(self):
        payment = Payment(user_id=1, amount=500, status='completed')
        assert payment.is_successful() is True

        payment.status = 'failed'
        assert payment.is_successful() is False

        payment.status = 'pending'
        assert payment.is_successful() is False


class TestVPNConfigModel:
    def test_vpn_config_creation(self):
        config = VPNConfig(
            user_id=1,
            marzban_user_id='test_user_123',
            config_url='vless://test-config',
            device_id='device_123'
        )
        assert config.user_id == 1
        assert config.marzban_user_id == 'test_user_123'
        assert config.config_url == 'vless://test-config'
        assert config.device_id == 'device_123'
        assert config.is_active is True

    def test_vpn_config_repr(self):
        config = VPNConfig(
            user_id=1,
            marzban_user_id='test_user_123'
        )
        assert repr(config) == "<VPNConfig(user_id=1, marzban_user_id='test_user_123')>"
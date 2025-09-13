"""
Sample data fixtures for tests
"""
from datetime import datetime, timedelta
from decimal import Decimal


# Sample user data
SAMPLE_USERS = [
    {
        'telegram_id': 123456789,
        'username': 'test_user1',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'en',
        'is_admin': False,
        'is_blocked': False
    },
    {
        'telegram_id': 987654321,
        'username': 'admin_user',
        'first_name': 'Admin',
        'last_name': 'User',
        'language_code': 'en',
        'is_admin': True,
        'is_blocked': False
    },
    {
        'telegram_id': 555666777,
        'username': 'blocked_user',
        'first_name': 'Blocked',
        'last_name': 'User',
        'language_code': 'ru',
        'is_admin': False,
        'is_blocked': True,
        'block_reason': 'Violation of terms'
    }
]

# Sample subscription data
SAMPLE_SUBSCRIPTIONS = [
    {
        'user_id': 1,
        'plan_type': 'trial',
        'status': 'active',
        'start_date': datetime.utcnow(),
        'end_date': datetime.utcnow() + timedelta(days=7),
        'is_trial': True,
        'auto_renewal': False
    },
    {
        'user_id': 2,
        'plan_type': 'monthly',
        'status': 'active',
        'start_date': datetime.utcnow() - timedelta(days=10),
        'end_date': datetime.utcnow() + timedelta(days=20),
        'is_trial': False,
        'auto_renewal': True
    },
    {
        'user_id': 3,
        'plan_type': 'monthly',
        'status': 'expired',
        'start_date': datetime.utcnow() - timedelta(days=40),
        'end_date': datetime.utcnow() - timedelta(days=10),
        'is_trial': False,
        'auto_renewal': False
    }
]

# Sample payment data
SAMPLE_PAYMENTS = [
    {
        'user_id': 1,
        'subscription_id': 1,
        'amount': Decimal('0.00'),
        'currency': 'RUB',
        'payment_method': 'trial',
        'payment_system': 'internal',
        'status': 'completed',
        'description': 'Trial activation'
    },
    {
        'user_id': 2,
        'subscription_id': 2,
        'amount': Decimal('500.00'),
        'currency': 'RUB',
        'payment_method': 'card',
        'payment_system': 'yookassa',
        'status': 'completed',
        'external_payment_id': 'yoo_123456',
        'description': 'Monthly subscription'
    },
    {
        'user_id': 3,
        'subscription_id': 3,
        'amount': Decimal('500.00'),
        'currency': 'RUB',
        'payment_method': 'card',
        'payment_system': 'yookassa',
        'status': 'failed',
        'external_payment_id': 'yoo_789012',
        'description': 'Failed payment'
    }
]

# Sample VPN config data
SAMPLE_VPN_CONFIGS = [
    {
        'user_id': 1,
        'marzban_user_id': 'trial_user_123456789',
        'config_url': 'vless://trial-config-url',
        'device_id': 'device_001',
        'is_active': True,
        'last_used_at': datetime.utcnow()
    },
    {
        'user_id': 2,
        'marzban_user_id': 'paid_user_987654321',
        'config_url': 'vless://paid-config-url',
        'device_id': 'device_002',
        'is_active': True,
        'last_used_at': datetime.utcnow() - timedelta(hours=2)
    }
]

# Sample usage stats data
SAMPLE_USAGE_STATS = [
    {
        'user_id': 1,
        'date': datetime.utcnow().date(),
        'bytes_uploaded': 1024 * 1024 * 100,  # 100MB
        'bytes_downloaded': 1024 * 1024 * 500,  # 500MB
        'connections_count': 5,
        'unique_ips': ['192.168.1.1', '10.0.0.1']
    },
    {
        'user_id': 2,
        'date': datetime.utcnow().date(),
        'bytes_uploaded': 1024 * 1024 * 200,  # 200MB
        'bytes_downloaded': 1024 * 1024 * 1000,  # 1GB
        'connections_count': 8,
        'unique_ips': ['192.168.1.2', '10.0.0.2', '172.16.0.1']
    }
]

# Sample referral stats data
SAMPLE_REFERRAL_STATS = [
    {
        'user_id': 2,
        'referral_count': 3,
        'bonus_days_earned': 21,
        'bonus_days_used': 7
    }
]

# Sample promo codes
SAMPLE_PROMO_CODES = [
    {
        'code': 'WELCOME50',
        'type': 'discount',
        'value': Decimal('50.00'),
        'max_uses': 100,
        'current_uses': 25,
        'valid_from': datetime.utcnow() - timedelta(days=30),
        'valid_until': datetime.utcnow() + timedelta(days=30),
        'is_active': True,
        'description': '50 RUB discount for new users'
    },
    {
        'code': 'BONUS7',
        'type': 'bonus_days',
        'value': Decimal('7'),
        'max_uses': 50,
        'current_uses': 10,
        'valid_from': datetime.utcnow() - timedelta(days=7),
        'valid_until': datetime.utcnow() + timedelta(days=23),
        'is_active': True,
        'description': '7 bonus days'
    }
]

# Sample system settings
SAMPLE_SYSTEM_SETTINGS = [
    {
        'key': 'maintenance_mode',
        'value': 'false',
        'description': 'System maintenance mode'
    },
    {
        'key': 'max_trial_users',
        'value': '1000',
        'description': 'Maximum number of trial users'
    },
    {
        'key': 'referral_bonus_days',
        'value': '7',
        'description': 'Bonus days for referral program'
    }
]

# Sample FAQ items
SAMPLE_FAQ_ITEMS = [
    {
        'question': 'Как начать использовать VPN?',
        'answer': 'Нажмите /start и следуйте инструкциям бота.',
        'category': 'getting_started',
        'order_index': 1,
        'is_active': True
    },
    {
        'question': 'Что делать если VPN не работает?',
        'answer': 'Попробуйте переподключиться или обратитесь в поддержку.',
        'category': 'troubleshooting',
        'order_index': 1,
        'is_active': True
    }
]

# Mock responses for external services
MOCK_MARZBAN_RESPONSES = {
    'create_user': {
        'username': 'test_user_123',
        'status': 'active',
        'data_limit': 107374182400,  # 100GB
        'expire': int((datetime.utcnow() + timedelta(days=30)).timestamp()),
        'links': ['vless://test-config-url@server:443?type=tcp&security=tls#test']
    },
    'get_user': {
        'username': 'test_user_123',
        'status': 'active',
        'used_traffic': 1073741824,  # 1GB used
        'data_limit': 107374182400,  # 100GB limit
        'expire': int((datetime.utcnow() + timedelta(days=25)).timestamp()),
        'links': ['vless://test-config-url@server:443?type=tcp&security=tls#test']
    }
}

MOCK_PAYMENT_RESPONSES = {
    'yookassa_create': {
        'id': 'yoo_123456789',
        'status': 'pending',
        'amount': {
            'value': '500.00',
            'currency': 'RUB'
        },
        'confirmation': {
            'type': 'redirect',
            'confirmation_url': 'https://yookassa.ru/checkout/payments/v2/contract'
        }
    },
    'yookassa_check': {
        'id': 'yoo_123456789',
        'status': 'succeeded',
        'amount': {
            'value': '500.00',
            'currency': 'RUB'
        },
        'paid': True
    }
}
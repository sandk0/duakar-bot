import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from typing import AsyncGenerator

from database.connection import Base
from api.main import app
from bot.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database"""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_marzban_client():
    """Mock Marzban client for tests"""
    from unittest.mock import AsyncMock
    
    client = AsyncMock()
    client.get_user.return_value = {
        'username': 'test_user',
        'status': 'active',
        'data_limit': 107374182400,  # 100GB
        'expire': 1234567890,
        'links': ['vless://test-config']
    }
    client.create_user.return_value = {
        'username': 'test_user',
        'status': 'active',
        'links': ['vless://test-config']
    }
    
    return client


@pytest.fixture
def mock_payment_provider():
    """Mock payment provider for tests"""
    from unittest.mock import AsyncMock
    
    provider = AsyncMock()
    provider.create_payment.return_value = {
        'success': True,
        'payment_url': 'https://test-payment.com/pay/123',
        'payment_id': 'test_payment_123'
    }
    provider.check_payment_status.return_value = {
        'status': 'completed',
        'amount': 500.00
    }
    
    return provider


@pytest.fixture
def sample_user_data():
    """Sample user data for tests"""
    return {
        'telegram_id': 123456789,
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'en'
    }


@pytest.fixture
def sample_subscription_data():
    """Sample subscription data for tests"""
    return {
        'plan_type': 'monthly',
        'status': 'active',
        'is_trial': False,
        'auto_renewal': True
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for tests"""
    return {
        'amount': 500.00,
        'currency': 'RUB',
        'payment_method': 'card',
        'payment_system': 'yookassa',
        'status': 'pending'
    }
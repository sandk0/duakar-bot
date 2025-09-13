import pytest
from httpx import AsyncClient
from unittest.mock import patch


class TestAuthAPI:
    async def test_login_success(self, client: AsyncClient):
        """Test successful login"""
        # Mock successful authentication
        with patch('api.dependencies.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                'id': 1,
                'telegram_id': 123456789,
                'username': 'admin',
                'is_admin': True
            }
            
            response = await client.post("/api/v1/auth/login", json={
                'username': 'admin',
                'password': 'password'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'token' in data['data']

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials"""
        response = await client.post("/api/v1/auth/login", json={
            'username': 'invalid',
            'password': 'wrong'
        })
        
        assert response.status_code == 401


class TestUsersAPI:
    async def test_get_users_unauthorized(self, client: AsyncClient):
        """Test getting users without authentication"""
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 401

    async def test_get_users_authorized(self, client: AsyncClient):
        """Test getting users with authentication"""
        # Mock authentication
        with patch('api.dependencies.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {
                'id': 1,
                'is_admin': True
            }
            
            response = await client.get("/api/v1/admin/users", headers={
                'Authorization': 'Bearer mock-token'
            })
            
            assert response.status_code == 200


class TestSubscriptionsAPI:
    async def test_get_subscriptions(self, client: AsyncClient):
        """Test getting subscriptions list"""
        with patch('api.dependencies.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'id': 1, 'is_admin': True}
            
            response = await client.get("/api/v1/admin/subscriptions", headers={
                'Authorization': 'Bearer mock-token'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert 'subscriptions' in data
            assert 'pagination' in data


class TestPaymentsAPI:
    async def test_get_payments(self, client: AsyncClient):
        """Test getting payments list"""
        with patch('api.dependencies.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'id': 1, 'is_admin': True}
            
            response = await client.get("/api/v1/admin/payments", headers={
                'Authorization': 'Bearer mock-token'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert 'payments' in data

    async def test_webhook_yookassa(self, client: AsyncClient):
        """Test YooKassa webhook processing"""
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'test_payment_id',
                'status': 'succeeded',
                'amount': {
                    'value': '500.00',
                    'currency': 'RUB'
                }
            }
        }
        
        response = await client.post("/api/v1/payments/webhooks/yookassa", json=webhook_data)
        
        # Should return 200 even if payment not found (for idempotency)
        assert response.status_code == 200


class TestSettingsAPI:
    async def test_get_settings(self, client: AsyncClient):
        """Test getting system settings"""
        with patch('api.dependencies.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'id': 1, 'is_admin': True}
            
            response = await client.get("/api/v1/admin/settings", headers={
                'Authorization': 'Bearer mock-token'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert 'settings' in data
            assert 'testing_mode' in data

    async def test_toggle_testing_mode(self, client: AsyncClient):
        """Test toggling testing mode"""
        with patch('api.dependencies.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'id': 1, 'is_admin': True}
            
            response = await client.post("/api/v1/admin/toggle-testing-mode", 
                                       json={'testing_mode': True},
                                       headers={'Authorization': 'Bearer mock-token'})
            
            assert response.status_code == 200
            data = response.json()
            assert data['testing_mode'] is True
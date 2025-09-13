import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from bot.config import settings
from .models import (
    MarzbanUser, CreateUserRequest, UpdateUserRequest,
    UserUsageResponse, SystemStats, AdminToken, UserStatus
)
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry failed requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            raise last_exception
        return wrapper
    return decorator


class MarzbanClient:
    def __init__(self):
        self.base_url = settings.marzban_api_url.rstrip('/')
        self.username = settings.marzban_admin_username
        self.password = settings.marzban_admin_password
        self.token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def authenticate(self) -> str:
        """Authenticate with Marzban API and get access token"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/admin/token",
                data={
                    "username": self.username,
                    "password": self.password,
                    "grant_type": "password"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data["access_token"]
            # Token expires in 1 hour by default
            self.token_expires = datetime.now() + timedelta(hours=1)
            
            logger.info("Successfully authenticated with Marzban API")
            return self.token
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to authenticate with Marzban: {str(e)}")
            raise
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        token = await self.authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @retry_on_failure(max_retries=3)
    async def create_user(
        self,
        username: str,
        expire_days: Optional[int] = None,
        data_limit_gb: Optional[int] = None,
        note: Optional[str] = None
    ) -> MarzbanUser:
        """Create a new user in Marzban"""
        headers = await self._get_headers()
        
        expire_timestamp = None
        if expire_days:
            expire_timestamp = int((datetime.now() + timedelta(days=expire_days)).timestamp())
        
        data_limit_bytes = None
        if data_limit_gb:
            data_limit_bytes = data_limit_gb * 1024 * 1024 * 1024
        
        request_data = CreateUserRequest(
            username=username,
            expire=expire_timestamp,
            data_limit=data_limit_bytes,
            note=note,
            inbounds={"vless": ["VLESS TCP REALITY"]},
            excluded_inbounds={"vless": []}  # Explicitly set empty exclusions
        )
        
        try:
            request_json = request_data.model_dump(exclude_none=True)
            logger.info(f"Creating Marzban user with data: {request_json}")
            
            response = await self.client.post(
                f"{self.base_url}/api/user",
                headers=headers,
                json=request_json
            )
            response.raise_for_status()
            
            user_data = response.json()
            logger.info(f"Created Marzban user: {username}")
            return MarzbanUser(**user_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to create user {username}: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3)
    async def get_user(self, username: str) -> Optional[MarzbanUser]:
        """Get user information from Marzban"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/user/{username}",
                headers=headers
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            user_data = response.json()
            return MarzbanUser(**user_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get user {username}: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3)
    async def update_user(
        self,
        username: str,
        expire_days: Optional[int] = None,
        data_limit_gb: Optional[int] = None,
        status: Optional[UserStatus] = None,
        excluded_inbounds: Optional[Dict[str, List[str]]] = None
    ) -> MarzbanUser:
        """Update existing user in Marzban"""
        headers = await self._get_headers()
        
        update_data = {}
        
        if expire_days is not None:
            update_data["expire"] = int((datetime.now() + timedelta(days=expire_days)).timestamp())
        
        if data_limit_gb is not None:
            update_data["data_limit"] = data_limit_gb * 1024 * 1024 * 1024
        
        if status is not None:
            update_data["status"] = status
        
        if excluded_inbounds is not None:
            update_data["excluded_inbounds"] = excluded_inbounds
            logger.info(f"Setting excluded_inbounds to: {excluded_inbounds}")
        
        # Always include the user in VLESS TCP REALITY
        update_data["inbounds"] = {"vless": ["VLESS TCP REALITY"]}
        
        try:
            logger.info(f"Updating user {username} with data: {update_data}")
            response = await self.client.put(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                json=update_data
            )
            response.raise_for_status()
            
            user_data = response.json()
            logger.info(f"Updated Marzban user: {username}")
            return MarzbanUser(**user_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to update user {username}: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3)
    async def delete_user(self, username: str) -> bool:
        """Delete user from Marzban"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/user/{username}",
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Deleted Marzban user: {username}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete user {username}: {str(e)}")
            return False
    
    @retry_on_failure(max_retries=3)
    async def reset_user_data_usage(self, username: str) -> bool:
        """Reset user's data usage"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/user/{username}/reset",
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Reset data usage for user: {username}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to reset user data {username}: {str(e)}")
            return False
    
    @retry_on_failure(max_retries=3)
    async def get_user_usage(self, username: str) -> Optional[UserUsageResponse]:
        """Get user usage statistics"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/user/{username}/usage",
                headers=headers
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            usage_data = response.json()
            return UserUsageResponse(**usage_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get user usage {username}: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3)
    async def get_system_stats(self) -> SystemStats:
        """Get system statistics from Marzban"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/system",
                headers=headers
            )
            response.raise_for_status()
            
            stats_data = response.json()
            return SystemStats(**stats_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get system stats: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3)
    async def get_users_list(
        self,
        offset: int = 0,
        limit: int = 50,
        username: Optional[str] = None,
        status: Optional[UserStatus] = None
    ) -> List[MarzbanUser]:
        """Get list of users from Marzban"""
        headers = await self._get_headers()
        
        params = {
            "offset": offset,
            "limit": limit
        }
        
        if username:
            params["username"] = username
        if status:
            params["status"] = status
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/users",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            users_data = response.json()
            return [MarzbanUser(**user) for user in users_data.get("users", [])]
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get users list: {str(e)}")
            raise
    
    async def revoke_user_subscription(self, username: str) -> bool:
        """Revoke user's subscription URL"""
        headers = await self._get_headers()
        
        try:
            response = await self.client.put(
                f"{self.base_url}/api/user/{username}/revoke_sub",
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Revoked subscription for user: {username}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to revoke subscription {username}: {str(e)}")
            return False
    
    async def get_user_config(self, username: str) -> Optional[str]:
        """Get user's VLESS configuration URL"""
        user = await self.get_user(username)
        if not user or not user.links:
            return None
        
        # Return the first VLESS link
        for link in user.links:
            if link.startswith("vless://"):
                return link
        
        return user.links[0] if user.links else None


# Singleton instance
marzban_client = MarzbanClient()
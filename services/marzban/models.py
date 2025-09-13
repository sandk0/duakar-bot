from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProxyProtocol(str, Enum):
    VLESS = "vless"
    VMESS = "vmess"
    TROJAN = "trojan"
    SHADOWSOCKS = "shadowsocks"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LIMITED = "limited"
    EXPIRED = "expired"


class MarzbanUser(BaseModel):
    username: str
    proxies: Dict[str, Any]
    expire: Optional[int] = None  # Unix timestamp
    data_limit: Optional[int] = None  # in bytes
    data_limit_reset_strategy: str = "no_reset"
    status: UserStatus = UserStatus.ACTIVE
    used_traffic: int = 0
    lifetime_used_traffic: int = 0
    created_at: datetime
    links: Optional[List[str]] = []
    subscription_url: Optional[str] = None
    excluded_inbounds: Dict[str, List[str]] = {}


class CreateUserRequest(BaseModel):
    username: str
    proxies: Dict[str, Any] = {
        "vless": {}
    }
    expire: Optional[int] = None
    data_limit: Optional[int] = None
    data_limit_reset_strategy: str = "no_reset"
    status: UserStatus = UserStatus.ACTIVE
    note: Optional[str] = None
    on_hold_expire_duration: Optional[int] = None
    on_hold_timeout: Optional[str] = None
    inbounds: Dict[str, List[str]] = {"vless": ["VLESS TCP REALITY"]}
    excluded_inbounds: Dict[str, List[str]] = {"vless": []}


class UpdateUserRequest(BaseModel):
    proxies: Optional[Dict[str, Any]] = None
    expire: Optional[int] = None
    data_limit: Optional[int] = None
    data_limit_reset_strategy: Optional[str] = None
    status: Optional[UserStatus] = None
    note: Optional[str] = None
    on_hold_expire_duration: Optional[int] = None
    on_hold_timeout: Optional[str] = None
    excluded_inbounds: Optional[Dict[str, List[str]]] = {}


class UserUsageResponse(BaseModel):
    username: str
    used_traffic: int
    lifetime_used_traffic: int
    data_limit: Optional[int]
    expire: Optional[int]
    status: UserStatus
    online_at: Optional[datetime]
    links: List[str]


class SystemStats(BaseModel):
    version: str
    mem_total: int
    mem_used: int
    cpu_cores: int
    cpu_usage: float
    total_user: int
    users_active: int
    incoming_bandwidth: int
    outgoing_bandwidth: int
    incoming_bandwidth_speed: int
    outgoing_bandwidth_speed: int


class NodeStatus(BaseModel):
    name: str
    id: str
    address: str
    port: int
    api_port: int
    usage_coefficient: float
    status: str
    message: Optional[str]


class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
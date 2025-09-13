from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Telegram
    bot_token: str
    bot_username: Optional[str] = None
    
    # Database
    database_url: str
    redis_url: str
    
    # Marzban
    marzban_api_url: str
    marzban_api_token: Optional[str] = None
    marzban_admin_username: str
    marzban_admin_password: str
    
    # Payment Systems
    wata_api_key: Optional[str] = None
    wata_secret_key: Optional[str] = None
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None
    
    # Security
    secret_key: str
    jwt_secret_key: str
    encryption_key: Optional[str] = None
    
    # Monitoring
    sentry_dsn: Optional[str] = ""
    prometheus_port: int = 9090
    
    # Other
    support_username: str = "@support"
    timezone: str = "Europe/Moscow"
    debug: bool = False
    log_level: str = "INFO"
    
    # Testing mode
    testing_mode: bool = False  # Skip payments in testing mode
    
    # Trial settings
    trial_days: int = 7
    
    # Referral settings
    referral_bonus_days: int = 30
    referral_friend_bonus_days: int = 7
    
    # Notification settings
    notification_days_before_expiry: list[int] = [1, 2, 3]
    
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
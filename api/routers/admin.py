from fastapi import APIRouter, Depends, HTTPException, status
from database.connection import async_session_maker
from database.models import User, SystemSetting
from api.dependencies import get_current_admin_user
from sqlalchemy import select
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/testing-mode")
async def get_testing_mode(current_admin: User = Depends(get_current_admin_user)):
    """Get current testing mode status"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "testing_mode")
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                testing_mode = json.loads(setting.value).get("enabled", False)
            else:
                testing_mode = False
            
            return {
                "testing_mode": testing_mode,
                "description": "When enabled, payments are skipped and subscriptions are activated automatically"
            }
    
    except Exception as e:
        logger.error(f"Error getting testing mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get testing mode status"
        )


@router.post("/testing-mode")
async def set_testing_mode(
    enabled: bool,
    current_admin: User = Depends(get_current_admin_user)
):
    """Enable or disable testing mode"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "testing_mode")
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = json.dumps({"enabled": enabled})
            else:
                setting = SystemSetting(
                    key="testing_mode",
                    value=json.dumps({"enabled": enabled}),
                    description="Enable/disable testing mode for payments"
                )
                session.add(setting)
            
            await session.commit()
            
            # Update runtime configuration
            from bot.config import settings
            settings.testing_mode = enabled
            
            logger.info(f"Testing mode {'enabled' if enabled else 'disabled'} by admin {current_admin.telegram_id}")
            
            return {
                "success": True,
                "testing_mode": enabled,
                "message": f"Testing mode {'enabled' if enabled else 'disabled'} successfully"
            }
    
    except Exception as e:
        logger.error(f"Error setting testing mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set testing mode"
        )


@router.get("/system-info")
async def get_system_info(current_admin: User = Depends(get_current_admin_user)):
    """Get system information"""
    try:
        from bot.config import settings
        
        return {
            "bot_info": {
                "username": settings.bot_username,
                "debug_mode": settings.debug,
                "testing_mode": settings.testing_mode
            },
            "features": {
                "payments_enabled": not settings.testing_mode,
                "marzban_configured": bool(settings.marzban_api_url),
                "yookassa_configured": bool(settings.yookassa_shop_id),
                "wata_configured": bool(settings.wata_api_key)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system information"
        )
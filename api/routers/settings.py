from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from pydantic import BaseModel

from api.dependencies import get_current_admin_user
from database.connection import get_session as get_db
from database.models import User, SystemSettings
from bot.config import settings

router = APIRouter()


class SettingUpdate(BaseModel):
    key: str
    value: str
    description: str = None


class TestingModeToggle(BaseModel):
    testing_mode: bool


@router.get("/")
async def get_all_settings(
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get all system settings"""
    try:
        result = await session.execute(select(SystemSettings))
        db_settings = result.scalars().all()
        
        settings_dict = {setting.key: setting.value for setting in db_settings}
        
        return {
            "settings": settings_dict,
            "testing_mode": settings.testing_mode,
            "system_info": {
                "version": "1.0.0",
                "environment": "development" if settings.testing_mode else "production"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.post("/")
async def create_or_update_setting(
    setting: SettingUpdate,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create or update system setting"""
    try:
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == setting.key)
        )
        existing_setting = result.scalar_one_or_none()
        
        if existing_setting:
            existing_setting.value = setting.value
            if setting.description:
                existing_setting.description = setting.description
        else:
            new_setting = SystemSettings(
                key=setting.key,
                value=setting.value,
                description=setting.description
            )
            session.add(new_setting)
        
        await session.commit()
        
        return {
            "message": f"Setting '{setting.key}' updated successfully",
            "key": setting.key,
            "value": setting.value
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )


@router.get("/{key}")
async def get_setting(
    key: str,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get specific system setting"""
    try:
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        
        return {
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "updated_at": setting.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}"
        )


@router.delete("/{key}")
async def delete_setting(
    key: str,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete system setting"""
    try:
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        
        await session.delete(setting)
        await session.commit()
        
        return {"message": f"Setting '{key}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete setting: {str(e)}"
        )
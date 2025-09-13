from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, date

from api.dependencies import get_current_admin_user
from database.connection import get_session as get_db
from database.models import User, Subscription, VPNConfig, Payment
from services.marzban.client import MarzbanClient

router = APIRouter()


class SubscriptionUpdate(BaseModel):
    status: Optional[str] = None
    auto_renewal: Optional[bool] = None
    end_date: Optional[datetime] = None


class SubscriptionStats(BaseModel):
    total_active: int
    total_expired: int
    total_trial: int
    total_paid: int
    revenue_today: float
    revenue_month: float


@router.get("/")
async def get_subscriptions(
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    is_trial: Optional[bool] = Query(None),
    user_id: Optional[int] = Query(None)
) -> Dict[str, Any]:
    """Get subscriptions list with pagination and filtering"""
    try:
        offset = (page - 1) * limit
        
        query = select(Subscription).options(
            selectinload(Subscription.user),
            selectinload(Subscription.vpn_config),
            selectinload(Subscription.payments)
        )
        
        filters = []
        if status:
            filters.append(Subscription.status == status)
        if is_trial is not None:
            filters.append(Subscription.is_trial == is_trial)
        if user_id:
            filters.append(Subscription.user_id == user_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.offset(offset).limit(limit).order_by(Subscription.created_at.desc())
        
        result = await session.execute(query)
        subscriptions = result.scalars().all()
        
        count_query = select(func.count(Subscription.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        subscription_list = []
        for sub in subscriptions:
            subscription_data = {
                "id": sub.id,
                "user_id": sub.user_id,
                "user": {
                    "telegram_id": sub.user.telegram_id,
                    "username": sub.user.username,
                    "first_name": sub.user.first_name,
                    "last_name": sub.user.last_name
                } if sub.user else None,
                "plan_type": sub.plan_type,
                "status": sub.status,
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "auto_renewal": sub.auto_renewal,
                "is_trial": sub.is_trial,
                "created_at": sub.created_at,
                "vpn_config": {
                    "id": sub.vpn_config.id,
                    "marzban_user_id": sub.vpn_config.marzban_user_id,
                    "is_active": sub.vpn_config.is_active,
                    "last_used_at": sub.vpn_config.last_used_at
                } if sub.vpn_config else None,
                "payments_count": len(sub.payments) if sub.payments else 0
            }
            subscription_list.append(subscription_data)
        
        return {
            "subscriptions": subscription_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscriptions: {str(e)}"
        )


@router.get("/stats")
async def get_subscription_stats(
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> SubscriptionStats:
    """Get subscription statistics"""
    try:
        today = date.today()
        
        active_query = select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "active",
                Subscription.end_date > datetime.now()
            )
        )
        active_result = await session.execute(active_query)
        total_active = active_result.scalar()
        
        expired_query = select(func.count(Subscription.id)).where(
            or_(
                Subscription.status == "expired",
                and_(
                    Subscription.status == "active",
                    Subscription.end_date <= datetime.now()
                )
            )
        )
        expired_result = await session.execute(expired_query)
        total_expired = expired_result.scalar()
        
        trial_query = select(func.count(Subscription.id)).where(Subscription.is_trial == True)
        trial_result = await session.execute(trial_query)
        total_trial = trial_result.scalar()
        
        paid_query = select(func.count(Subscription.id)).where(Subscription.is_trial == False)
        paid_result = await session.execute(paid_query)
        total_paid = paid_result.scalar()
        
        revenue_today_query = select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "completed",
                func.date(Payment.created_at) == today
            )
        )
        revenue_today_result = await session.execute(revenue_today_query)
        revenue_today = float(revenue_today_result.scalar() or 0)
        
        revenue_month_query = select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "completed",
                func.extract('year', Payment.created_at) == today.year,
                func.extract('month', Payment.created_at) == today.month
            )
        )
        revenue_month_result = await session.execute(revenue_month_query)
        revenue_month = float(revenue_month_result.scalar() or 0)
        
        return SubscriptionStats(
            total_active=total_active,
            total_expired=total_expired,
            total_trial=total_trial,
            total_paid=total_paid,
            revenue_today=revenue_today,
            revenue_month=revenue_month
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription stats: {str(e)}"
        )


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get specific subscription details"""
    try:
        query = select(Subscription).options(
            selectinload(Subscription.user),
            selectinload(Subscription.vpn_config),
            selectinload(Subscription.payments)
        ).where(Subscription.id == subscription_id)
        
        result = await session.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "user": {
                "telegram_id": subscription.user.telegram_id,
                "username": subscription.user.username,
                "first_name": subscription.user.first_name,
                "last_name": subscription.user.last_name,
                "created_at": subscription.user.created_at
            } if subscription.user else None,
            "plan_type": subscription.plan_type,
            "status": subscription.status,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "auto_renewal": subscription.auto_renewal,
            "is_trial": subscription.is_trial,
            "created_at": subscription.created_at,
            "vpn_config": {
                "id": subscription.vpn_config.id,
                "marzban_user_id": subscription.vpn_config.marzban_user_id,
                "config_url": subscription.vpn_config.config_url,
                "device_id": subscription.vpn_config.device_id,
                "is_active": subscription.vpn_config.is_active,
                "created_at": subscription.vpn_config.created_at,
                "last_used_at": subscription.vpn_config.last_used_at
            } if subscription.vpn_config else None,
            "payments": [
                {
                    "id": payment.id,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "created_at": payment.created_at
                } for payment in subscription.payments
            ] if subscription.payments else []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription: {str(e)}"
        )


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdate,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update subscription"""
    try:
        result = await session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        if update_data.status is not None:
            subscription.status = update_data.status
        if update_data.auto_renewal is not None:
            subscription.auto_renewal = update_data.auto_renewal
        if update_data.end_date is not None:
            subscription.end_date = update_data.end_date
        
        await session.commit()
        
        return {
            "message": "Subscription updated successfully",
            "subscription_id": subscription_id,
            "updated_fields": update_data.dict(exclude_unset=True)
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )


@router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Cancel subscription and deactivate VPN config"""
    try:
        query = select(Subscription).options(
            selectinload(Subscription.vpn_config)
        ).where(Subscription.id == subscription_id)
        
        result = await session.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        subscription.status = "cancelled"
        subscription.auto_renewal = False
        
        if subscription.vpn_config and subscription.vpn_config.marzban_user_id:
            try:
                async with MarzbanClient() as client:
                    await client.disable_user(subscription.vpn_config.marzban_user_id)
                subscription.vpn_config.is_active = False
            except Exception as marzban_error:
                pass
        
        await session.commit()
        
        return {"message": f"Subscription {subscription_id} cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/{subscription_id}/extend")
async def extend_subscription(
    subscription_id: int,
    days: int = Query(..., ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Extend subscription by specified days"""
    try:
        result = await session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        from datetime import timedelta
        if subscription.end_date:
            new_end_date = subscription.end_date + timedelta(days=days)
        else:
            new_end_date = datetime.now() + timedelta(days=days)
        
        subscription.end_date = new_end_date
        if subscription.status == "expired":
            subscription.status = "active"
        
        await session.commit()
        
        return {
            "message": f"Subscription extended by {days} days",
            "subscription_id": subscription_id,
            "new_end_date": new_end_date
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extend subscription: {str(e)}"
        )
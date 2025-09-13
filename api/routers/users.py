from fastapi import APIRouter, Depends, HTTPException, status, Query
from database.connection import async_session_maker
from database.models import User, Subscription, Payment
from api.dependencies import get_current_admin_user
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    search: Optional[str] = None,
    blocked: Optional[bool] = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get list of users with pagination and filtering"""
    try:
        async with async_session_maker() as session:
            query = select(User)
            
            # Apply filters
            if search:
                query = query.where(
                    or_(
                        User.username.ilike(f"%{search}%"),
                        User.first_name.ilike(f"%{search}%"),
                        User.telegram_id.like(f"%{search}%")
                    )
                )
            
            if blocked is not None:
                query = query.where(User.is_blocked == blocked)
            
            # Get total count
            count_result = await session.execute(select(func.count()).select_from(query.subquery()))
            total = count_result.scalar()
            
            # Get users with pagination
            users_result = await session.execute(
                query.offset(skip).limit(limit).order_by(User.created_at.desc())
            )
            users = users_result.scalars().all()
            
            # Format response
            users_data = []
            for user in users:
                # Get user's active subscription
                sub_result = await session.execute(
                    select(Subscription)
                    .where(Subscription.user_id == user.id)
                    .order_by(Subscription.created_at.desc())
                    .limit(1)
                )
                latest_sub = sub_result.scalar_one_or_none()
                
                users_data.append({
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_blocked": user.is_blocked,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                    "subscription_status": latest_sub.status if latest_sub else None,
                    "subscription_end": latest_sub.end_date.isoformat() if latest_sub and latest_sub.end_date else None
                })
            
            return {
                "users": users_data,
                "total": total,
                "skip": skip,
                "limit": limit
            }
    
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get detailed user information"""
    try:
        async with async_session_maker() as session:
            # Get user
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get user's subscriptions
            subs_result = await session.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.created_at.desc())
            )
            subscriptions = subs_result.scalars().all()
            
            # Get user's payments
            payments_result = await session.execute(
                select(Payment)
                .where(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
                .limit(10)
            )
            payments = payments_result.scalars().all()
            
            return {
                "user": {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_blocked": user.is_blocked,
                    "block_reason": user.block_reason,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                },
                "subscriptions": [
                    {
                        "id": sub.id,
                        "plan_type": sub.plan_type,
                        "status": sub.status,
                        "start_date": sub.start_date.isoformat() if sub.start_date else None,
                        "end_date": sub.end_date.isoformat() if sub.end_date else None,
                        "is_trial": sub.is_trial,
                        "auto_renewal": sub.auto_renewal,
                        "created_at": sub.created_at.isoformat()
                    }
                    for sub in subscriptions
                ],
                "payments": [
                    {
                        "id": payment.id,
                        "amount": float(payment.amount),
                        "currency": payment.currency,
                        "status": payment.status,
                        "payment_method": payment.payment_method,
                        "created_at": payment.created_at.isoformat()
                    }
                    for payment in payments
                ]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.post("/{user_id}/block")
async def block_user(
    user_id: int,
    reason: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Block user"""
    try:
        async with async_session_maker() as session:
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user.is_blocked = True
            user.block_reason = reason
            
            await session.commit()
            
            logger.info(f"User {user_id} blocked by admin {current_admin.telegram_id}")
            
            return {"success": True, "message": "User blocked successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to block user"
        )


@router.post("/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user)
):
    """Unblock user"""
    try:
        async with async_session_maker() as session:
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user.is_blocked = False
            user.block_reason = None
            
            await session.commit()
            
            logger.info(f"User {user_id} unblocked by admin {current_admin.telegram_id}")
            
            return {"success": True, "message": "User unblocked successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unblock user"
        )
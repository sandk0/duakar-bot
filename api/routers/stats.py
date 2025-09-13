from fastapi import APIRouter, Depends, HTTPException, status, Query
from database.connection import async_session_maker
from database.models import User, Subscription, Payment, SubscriptionStatus
from database.models.payment import PaymentStatus
from api.dependencies import get_current_admin_user
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview")
async def get_overview_stats(current_admin: User = Depends(get_current_admin_user)):
    """Get overview statistics"""
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            
            # Total users
            total_users = await session.scalar(select(func.count(User.id)))
            
            # Active subscriptions
            active_subs = await session.scalar(
                select(func.count(Subscription.id))
                .where(
                    and_(
                        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                        Subscription.end_date > now
                    )
                )
            )
            
            # Total revenue
            total_revenue = await session.scalar(
                select(func.sum(Payment.amount))
                .where(Payment.status == PaymentStatus.SUCCESS)
            ) or 0
            
            # Monthly revenue (current month)
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_revenue = await session.scalar(
                select(func.sum(Payment.amount))
                .where(
                    and_(
                        Payment.status == PaymentStatus.SUCCESS,
                        Payment.created_at >= start_of_month
                    )
                )
            ) or 0
            
            # Daily stats (last 30 days)
            thirty_days_ago = now - timedelta(days=30)
            
            # New users last 30 days
            new_users_30d = await session.scalar(
                select(func.count(User.id))
                .where(User.created_at >= thirty_days_ago)
            ) or 0
            
            # Successful payments last 30 days
            payments_30d = await session.scalar(
                select(func.count(Payment.id))
                .where(
                    and_(
                        Payment.status == PaymentStatus.SUCCESS,
                        Payment.created_at >= thirty_days_ago
                    )
                )
            ) or 0
            
            # Testing mode status
            from bot.config import settings
            
            return {
                "total_users": total_users,
                "active_subscriptions": active_subs,
                "total_revenue": float(total_revenue),
                "monthly_revenue": float(monthly_revenue),
                "new_users_30d": new_users_30d,
                "payments_30d": payments_30d,
                "testing_mode": settings.testing_mode,
                "last_updated": now.isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overview statistics"
        )


@router.get("/revenue")
async def get_revenue_stats(
    days: int = Query(30, ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get revenue statistics for specified period"""
    try:
        async with async_session_maker() as session:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Daily revenue
            daily_revenue_query = text("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(amount) as revenue,
                    COUNT(*) as transactions
                FROM payments 
                WHERE status = 'success' 
                AND created_at >= :start_date 
                AND created_at <= :end_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            
            result = await session.execute(
                daily_revenue_query, 
                {"start_date": start_date, "end_date": end_date}
            )
            daily_data = result.fetchall()
            
            # Revenue by payment method
            method_revenue_query = select(
                Payment.payment_method,
                func.sum(Payment.amount).label("revenue"),
                func.count(Payment.id).label("transactions")
            ).where(
                and_(
                    Payment.status == PaymentStatus.SUCCESS,
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date
                )
            ).group_by(Payment.payment_method)
            
            method_result = await session.execute(method_revenue_query)
            method_data = method_result.all()
            
            # Total for period
            total_revenue = sum(row.revenue for row in daily_data) if daily_data else 0
            total_transactions = sum(row.transactions for row in daily_data) if daily_data else 0
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "total_revenue": float(total_revenue),
                "total_transactions": total_transactions,
                "average_transaction": float(total_revenue / total_transactions) if total_transactions > 0 else 0,
                "daily_revenue": [
                    {
                        "date": row.date.isoformat(),
                        "revenue": float(row.revenue),
                        "transactions": row.transactions
                    }
                    for row in daily_data
                ],
                "revenue_by_method": [
                    {
                        "method": row.payment_method,
                        "revenue": float(row.revenue),
                        "transactions": row.transactions
                    }
                    for row in method_data
                ]
            }
    
    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get revenue statistics"
        )


@router.get("/users")
async def get_user_stats(current_admin: User = Depends(get_current_admin_user)):
    """Get user statistics"""
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            
            # User registration stats (last 30 days)
            registration_query = text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as registrations
                FROM users 
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            
            thirty_days_ago = now - timedelta(days=30)
            reg_result = await session.execute(
                registration_query,
                {"start_date": thirty_days_ago}
            )
            registration_data = reg_result.fetchall()
            
            # Subscription status distribution
            status_query = select(
                Subscription.status,
                func.count(Subscription.id).label("count")
            ).group_by(Subscription.status)
            
            status_result = await session.execute(status_query)
            status_data = status_result.all()
            
            # Trial conversion rate
            total_trials = await session.scalar(
                select(func.count(Subscription.id))
                .where(Subscription.is_trial == True)
            ) or 0
            
            converted_trials = await session.scalar(
                select(func.count(User.id.distinct()))
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        User.id.in_(
                            select(Subscription.user_id)
                            .where(Subscription.is_trial == True)
                        ),
                        Subscription.is_trial == False,
                        Subscription.status == SubscriptionStatus.ACTIVE
                    )
                )
            ) or 0
            
            conversion_rate = (converted_trials / total_trials * 100) if total_trials > 0 else 0
            
            return {
                "registrations_30d": [
                    {
                        "date": row.date.isoformat(),
                        "registrations": row.registrations
                    }
                    for row in registration_data
                ],
                "subscription_distribution": [
                    {
                        "status": row.status,
                        "count": row.count
                    }
                    for row in status_data
                ],
                "trial_conversion": {
                    "total_trials": total_trials,
                    "converted_trials": converted_trials,
                    "conversion_rate": round(conversion_rate, 2)
                }
            }
    
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )
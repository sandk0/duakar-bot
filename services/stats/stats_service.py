import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from decimal import Decimal

from database.models import (
    User, Subscription, Payment, VPNConfig, 
    UsageStats, ReferralStats, ActionLog
)

logger = logging.getLogger(__name__)


class StatsService:
    """Service for collecting and analyzing statistics"""
    
    async def get_dashboard_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """Get main dashboard statistics"""
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {}
        
        # User statistics
        stats['users'] = await self._get_user_stats(session, today, week_ago, month_ago)
        
        # Subscription statistics
        stats['subscriptions'] = await self._get_subscription_stats(session, today, week_ago, month_ago)
        
        # Payment statistics
        stats['payments'] = await self._get_payment_stats(session, today, week_ago, month_ago)
        
        # VPN usage statistics
        stats['vpn_usage'] = await self._get_vpn_usage_stats(session, today, week_ago, month_ago)
        
        # System statistics
        stats['system'] = await self._get_system_stats(session)
        
        return stats
    
    async def _get_user_stats(
        self, 
        session: AsyncSession, 
        today: date, 
        week_ago: date, 
        month_ago: date
    ) -> Dict[str, Any]:
        """Get user statistics"""
        
        # Total users
        total_result = await session.execute(select(func.count(User.id)))
        total_users = total_result.scalar()
        
        # Active users (have active subscription)
        active_result = await session.execute(
            select(func.count(User.id.distinct())).select_from(
                User.__table__.join(Subscription.__table__)
            ).where(
                and_(
                    Subscription.status == 'active',
                    Subscription.end_date > datetime.utcnow()
                )
            )
        )
        active_users = active_result.scalar()
        
        # Blocked users
        blocked_result = await session.execute(
            select(func.count(User.id)).where(User.is_blocked == True)
        )
        blocked_users = blocked_result.scalar()
        
        # New users today
        today_result = await session.execute(
            select(func.count(User.id)).where(
                func.date(User.created_at) == today
            )
        )
        new_users_today = today_result.scalar()
        
        # New users this week
        week_result = await session.execute(
            select(func.count(User.id)).where(
                User.created_at >= week_ago
            )
        )
        new_users_week = week_result.scalar()
        
        # New users this month
        month_result = await session.execute(
            select(func.count(User.id)).where(
                User.created_at >= month_ago
            )
        )
        new_users_month = month_result.scalar()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'blocked_users': blocked_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month
        }
    
    async def _get_subscription_stats(
        self, 
        session: AsyncSession, 
        today: date, 
        week_ago: date, 
        month_ago: date
    ) -> Dict[str, Any]:
        """Get subscription statistics"""
        
        # Total subscriptions
        total_result = await session.execute(select(func.count(Subscription.id)))
        total_subscriptions = total_result.scalar()
        
        # Active subscriptions
        active_result = await session.execute(
            select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == 'active',
                    Subscription.end_date > datetime.utcnow()
                )
            )
        )
        active_subscriptions = active_result.scalar()
        
        # Expired subscriptions
        expired_result = await session.execute(
            select(func.count(Subscription.id)).where(
                or_(
                    Subscription.status == 'expired',
                    and_(
                        Subscription.status == 'active',
                        Subscription.end_date <= datetime.utcnow()
                    )
                )
            )
        )
        expired_subscriptions = expired_result.scalar()
        
        # Trial subscriptions
        trial_result = await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_trial == True)
        )
        trial_subscriptions = trial_result.scalar()
        
        # New subscriptions today
        new_today_result = await session.execute(
            select(func.count(Subscription.id)).where(
                func.date(Subscription.created_at) == today
            )
        )
        new_subscriptions_today = new_today_result.scalar()
        
        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'expired_subscriptions': expired_subscriptions,
            'trial_subscriptions': trial_subscriptions,
            'paid_subscriptions': total_subscriptions - trial_subscriptions,
            'new_subscriptions_today': new_subscriptions_today
        }
    
    async def _get_payment_stats(
        self, 
        session: AsyncSession, 
        today: date, 
        week_ago: date, 
        month_ago: date
    ) -> Dict[str, Any]:
        """Get payment statistics"""
        
        # Total payments
        total_result = await session.execute(select(func.count(Payment.id)))
        total_payments = total_result.scalar()
        
        # Successful payments
        successful_result = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == 'completed')
        )
        successful_payments = successful_result.scalar()
        
        # Failed payments
        failed_result = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == 'failed')
        )
        failed_payments = failed_result.scalar()
        
        # Total revenue
        total_revenue_result = await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == 'completed')
        )
        total_revenue = total_revenue_result.scalar() or Decimal('0')
        
        # Revenue today
        revenue_today_result = await session.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.status == 'completed',
                    func.date(Payment.created_at) == today
                )
            )
        )
        revenue_today = revenue_today_result.scalar() or Decimal('0')
        
        # Revenue this month
        revenue_month_result = await session.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.status == 'completed',
                    Payment.created_at >= month_ago
                )
            )
        )
        revenue_month = revenue_month_result.scalar() or Decimal('0')
        
        # Average payment amount
        avg_payment_result = await session.execute(
            select(func.avg(Payment.amount)).where(Payment.status == 'completed')
        )
        avg_payment = avg_payment_result.scalar() or Decimal('0')
        
        return {
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'pending_payments': total_payments - successful_payments - failed_payments,
            'total_revenue': float(total_revenue),
            'revenue_today': float(revenue_today),
            'revenue_month': float(revenue_month),
            'average_payment': float(avg_payment),
            'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0
        }
    
    async def _get_vpn_usage_stats(
        self, 
        session: AsyncSession, 
        today: date, 
        week_ago: date, 
        month_ago: date
    ) -> Dict[str, Any]:
        """Get VPN usage statistics"""
        
        # Active VPN configs
        active_configs_result = await session.execute(
            select(func.count(VPNConfig.id)).where(VPNConfig.is_active == True)
        )
        active_configs = active_configs_result.scalar()
        
        # Total data usage this month
        data_usage_result = await session.execute(
            select(
                func.sum(UsageStats.bytes_uploaded + UsageStats.bytes_downloaded)
            ).where(
                UsageStats.date >= month_ago.replace(day=1)
            )
        )
        total_data_usage = data_usage_result.scalar() or 0
        
        # Active users today (who used VPN)
        active_today_result = await session.execute(
            select(func.count(VPNConfig.id.distinct())).where(
                func.date(VPNConfig.last_used_at) == today
            )
        )
        active_today = active_today_result.scalar()
        
        return {
            'active_vpn_configs': active_configs,
            'total_data_usage_gb': round(total_data_usage / (1024**3), 2),
            'active_users_today': active_today
        }
    
    async def _get_system_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """Get system statistics"""
        
        # Database size (approximate)
        db_size_result = await session.execute(
            text("SELECT pg_database_size(current_database())")
        )
        db_size = db_size_result.scalar() or 0
        
        # Recent errors count
        week_ago = datetime.utcnow() - timedelta(days=7)
        errors_result = await session.execute(
            select(func.count(ActionLog.id)).where(
                and_(
                    ActionLog.action_type.like('%error%'),
                    ActionLog.created_at >= week_ago
                )
            )
        )
        recent_errors = errors_result.scalar()
        
        return {
            'database_size_mb': round(db_size / (1024**2), 2),
            'recent_errors': recent_errors
        }
    
    async def get_user_growth_chart(
        self, 
        session: AsyncSession, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get user growth data for chart"""
        start_date = date.today() - timedelta(days=days)
        
        result = await session.execute(
            select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            ).where(
                User.created_at >= start_date
            ).group_by(
                func.date(User.created_at)
            ).order_by('date')
        )
        
        growth_data = []
        for row in result:
            growth_data.append({
                'date': row.date.strftime('%Y-%m-%d'),
                'count': row.count
            })
        
        return growth_data
    
    async def get_revenue_chart(
        self, 
        session: AsyncSession, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get revenue data for chart"""
        start_date = date.today() - timedelta(days=days)
        
        result = await session.execute(
            select(
                func.date(Payment.created_at).label('date'),
                func.sum(Payment.amount).label('revenue')
            ).where(
                and_(
                    Payment.status == 'completed',
                    Payment.created_at >= start_date
                )
            ).group_by(
                func.date(Payment.created_at)
            ).order_by('date')
        )
        
        revenue_data = []
        for row in result:
            revenue_data.append({
                'date': row.date.strftime('%Y-%m-%d'),
                'revenue': float(row.revenue or 0)
            })
        
        return revenue_data
    
    async def get_referral_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """Get referral system statistics"""
        
        # Total referrals
        total_referrals_result = await session.execute(
            select(func.sum(ReferralStats.referral_count))
        )
        total_referrals = total_referrals_result.scalar() or 0
        
        # Total bonus days earned
        bonus_days_result = await session.execute(
            select(func.sum(ReferralStats.bonus_days_earned))
        )
        total_bonus_days = bonus_days_result.scalar() or 0
        
        # Top referrers
        top_referrers_result = await session.execute(
            select(
                User.username,
                ReferralStats.referral_count,
                ReferralStats.bonus_days_earned
            ).select_from(
                ReferralStats.__table__.join(User.__table__)
            ).order_by(
                ReferralStats.referral_count.desc()
            ).limit(10)
        )
        
        top_referrers = []
        for row in top_referrers_result:
            top_referrers.append({
                'username': row.username or 'Anonymous',
                'referrals': row.referral_count,
                'bonus_days': row.bonus_days_earned
            })
        
        return {
            'total_referrals': total_referrals,
            'total_bonus_days': total_bonus_days,
            'top_referrers': top_referrers
        }
    
    async def get_user_activity_report(
        self, 
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Get detailed user activity report"""
        
        # User basic info
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {}
        
        # User subscriptions
        subscriptions_result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscriptions = subscriptions_result.scalars().all()
        
        # User payments
        payments_result = await session.execute(
            select(Payment).where(Payment.user_id == user_id)
        )
        payments = payments_result.scalars().all()
        
        # Usage statistics
        usage_result = await session.execute(
            select(UsageStats).where(UsageStats.user_id == user_id)
        )
        usage_stats = usage_result.scalars().all()
        
        total_data_usage = sum(
            (stat.bytes_uploaded or 0) + (stat.bytes_downloaded or 0) 
            for stat in usage_stats
        )
        
        return {
            'user_info': {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'created_at': user.created_at
            },
            'subscription_count': len(subscriptions),
            'payment_count': len(payments),
            'total_spent': sum(p.amount for p in payments if p.status == 'completed'),
            'total_data_usage_gb': round(total_data_usage / (1024**3), 2),
            'last_activity': max(
                [s.created_at for s in subscriptions] + 
                [p.created_at for p in payments] +
                [user.created_at]
            ) if subscriptions or payments else user.created_at
        }
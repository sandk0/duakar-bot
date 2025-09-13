from celery import shared_task
from database.connection import async_session_maker
from database.models import User, Subscription, Payment, UsageStat, VPNConfig, SubscriptionStatus
from services.marzban import marzban_client
from sqlalchemy import select, func, and_
from datetime import datetime, date, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def collect_daily_stats(self):
    """Collect daily usage statistics"""
    return asyncio.run(_collect_daily_stats())


async def _collect_daily_stats():
    """Async implementation of daily stats collection"""
    try:
        async with async_session_maker() as session:
            today = date.today()
            
            # Collect stats for all active VPN users
            result = await session.execute(
                select(VPNConfig, User)
                .join(User, VPNConfig.user_id == User.id)
                .where(VPNConfig.is_active == True)
            )
            
            vpn_configs = result.all()
            
            for vpn_config, user in vpn_configs:
                try:
                    # Get usage data from Marzban
                    async with marzban_client as client:
                        usage_data = await client.get_user_usage(vpn_config.marzban_user_id)
                        
                        if usage_data:
                            # Check if stats for today already exist
                            result = await session.execute(
                                select(UsageStat)
                                .where(
                                    and_(
                                        UsageStat.user_id == user.id,
                                        UsageStat.date == today
                                    )
                                )
                            )
                            
                            daily_stat = result.scalar_one_or_none()
                            
                            if not daily_stat:
                                # Create new daily stat
                                daily_stat = UsageStat(
                                    user_id=user.id,
                                    date=today,
                                    bytes_uploaded=usage_data.used_traffic,
                                    bytes_downloaded=0,  # Marzban doesn't separate up/down
                                    connections_count=1 if usage_data.online_at else 0
                                )
                                session.add(daily_stat)
                            else:
                                # Update existing stat
                                daily_stat.bytes_uploaded = usage_data.used_traffic
                                daily_stat.connections_count = 1 if usage_data.online_at else 0
                            
                            logger.debug(f"Updated usage stats for user {user.telegram_id}")
                
                except Exception as e:
                    logger.error(f"Error collecting stats for user {user.telegram_id}: {e}")
                    continue
            
            await session.commit()
            logger.info(f"Collected daily stats for {len(vpn_configs)} users")
            
    except Exception as e:
        logger.error(f"Error in collect_daily_stats: {e}")
        raise


@shared_task(bind=True)
def sync_vpn_usage(self):
    """Sync VPN usage data from Marzban"""
    return asyncio.run(_sync_vpn_usage())


async def _sync_vpn_usage():
    """Async implementation of VPN usage sync"""
    try:
        async with async_session_maker() as session:
            # Get all active VPN configs
            result = await session.execute(
                select(VPNConfig, User)
                .join(User, VPNConfig.user_id == User.id)
                .where(VPNConfig.is_active == True)
            )
            
            vpn_configs = result.all()
            sync_count = 0
            
            for vpn_config, user in vpn_configs:
                try:
                    async with marzban_client as client:
                        # Get user data from Marzban
                        marzban_user = await client.get_user(vpn_config.marzban_user_id)
                        
                        if marzban_user:
                            # Update last used time if user is online
                            if hasattr(marzban_user, 'online_at') and marzban_user.online_at:
                                vpn_config.last_used_at = datetime.now()
                            
                            # Check if user status matches subscription
                            result = await session.execute(
                                select(Subscription)
                                .where(
                                    and_(
                                        Subscription.user_id == user.id,
                                        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                                    )
                                )
                            )
                            
                            subscription = result.scalar_one_or_none()
                            
                            # Sync user status in Marzban with subscription status
                            if subscription and subscription.end_date > datetime.now():
                                if marzban_user.status.value != "active":
                                    from services.marzban import UserStatus
                                    await client.update_user(
                                        username=vpn_config.marzban_user_id,
                                        status=UserStatus.ACTIVE
                                    )
                                    logger.info(f"Activated Marzban user {vpn_config.marzban_user_id}")
                            else:
                                if marzban_user.status.value != "disabled":
                                    from services.marzban import UserStatus
                                    await client.update_user(
                                        username=vpn_config.marzban_user_id,
                                        status=UserStatus.DISABLED
                                    )
                                    vpn_config.is_active = False
                                    logger.info(f"Disabled Marzban user {vpn_config.marzban_user_id}")
                            
                            sync_count += 1
                
                except Exception as e:
                    logger.error(f"Error syncing VPN usage for user {user.telegram_id}: {e}")
                    continue
            
            if sync_count > 0:
                await session.commit()
                logger.info(f"Synced VPN usage for {sync_count} users")
            
    except Exception as e:
        logger.error(f"Error in sync_vpn_usage: {e}")
        raise


@shared_task(bind=True)
def check_server_health(self):
    """Check VPN server health"""
    return asyncio.run(_check_server_health())


async def _check_server_health():
    """Async implementation of server health check"""
    try:
        async with marzban_client as client:
            # Get system stats from Marzban
            system_stats = await client.get_system_stats()
            
            # Log basic health metrics
            logger.info(f"Server health - CPU: {system_stats.cpu_usage}%, Memory: {system_stats.mem_used}/{system_stats.mem_total}")
            logger.info(f"Active users: {system_stats.users_active}/{system_stats.total_user}")
            
            # Check for critical issues
            if system_stats.cpu_usage > 90:
                logger.warning(f"High CPU usage: {system_stats.cpu_usage}%")
            
            if (system_stats.mem_used / system_stats.mem_total) > 0.9:
                logger.warning(f"High memory usage: {(system_stats.mem_used / system_stats.mem_total * 100):.1f}%")
            
            return {
                "status": "healthy",
                "cpu_usage": system_stats.cpu_usage,
                "memory_usage": system_stats.mem_used / system_stats.mem_total * 100,
                "active_users": system_stats.users_active,
                "total_users": system_stats.total_user
            }
            
    except Exception as e:
        logger.error(f"Server health check failed: {e}")
        
        # Could send alert to admin here
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@shared_task(bind=True)
def generate_revenue_report(self, start_date: str, end_date: str):
    """Generate revenue report for date range"""
    return asyncio.run(_generate_revenue_report(start_date, end_date))


async def _generate_revenue_report(start_date_str: str, end_date_str: str):
    """Async implementation of revenue report generation"""
    try:
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        
        async with async_session_maker() as session:
            from database.models.payment import PaymentStatus
            
            # Get successful payments in date range
            result = await session.execute(
                select(
                    func.sum(Payment.amount),
                    func.count(Payment.id),
                    Payment.payment_method
                )
                .where(
                    and_(
                        Payment.status == PaymentStatus.SUCCESS,
                        Payment.created_at >= start_date,
                        Payment.created_at <= end_date
                    )
                )
                .group_by(Payment.payment_method)
            )
            
            revenue_by_method = result.all()
            
            # Total revenue
            total_revenue = await session.scalar(
                select(func.sum(Payment.amount))
                .where(
                    and_(
                        Payment.status == PaymentStatus.SUCCESS,
                        Payment.created_at >= start_date,
                        Payment.created_at <= end_date
                    )
                )
            ) or 0
            
            # Total transactions
            total_transactions = await session.scalar(
                select(func.count(Payment.id))
                .where(
                    and_(
                        Payment.status == PaymentStatus.SUCCESS,
                        Payment.created_at >= start_date,
                        Payment.created_at <= end_date
                    )
                )
            ) or 0
            
            # New users in period
            new_users = await session.scalar(
                select(func.count(User.id))
                .where(
                    and_(
                        User.created_at >= start_date,
                        User.created_at <= end_date
                    )
                )
            ) or 0
            
            report = {
                "period": {
                    "start": start_date_str,
                    "end": end_date_str
                },
                "total_revenue": float(total_revenue),
                "total_transactions": total_transactions,
                "new_users": new_users,
                "revenue_by_method": [
                    {
                        "method": method,
                        "revenue": float(revenue),
                        "transactions": count
                    }
                    for revenue, count, method in revenue_by_method
                ],
                "average_transaction": float(total_revenue / total_transactions) if total_transactions > 0 else 0
            }
            
            logger.info(f"Generated revenue report for {start_date_str} to {end_date_str}")
            return report
            
    except Exception as e:
        logger.error(f"Error generating revenue report: {e}")
        raise


@shared_task(bind=True)
def calculate_user_metrics(self):
    """Calculate user engagement metrics"""
    return asyncio.run(_calculate_user_metrics())


async def _calculate_user_metrics():
    """Async implementation of user metrics calculation"""
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            
            # Active users (have active subscription)
            active_users = await session.scalar(
                select(func.count(User.id.distinct()))
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                        Subscription.end_date > now
                    )
                )
            ) or 0
            
            # Churn rate (users who expired in last 30 days)
            thirty_days_ago = now - timedelta(days=30)
            churned_users = await session.scalar(
                select(func.count(Subscription.id))
                .where(
                    and_(
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        Subscription.end_date >= thirty_days_ago,
                        Subscription.end_date <= now
                    )
                )
            ) or 0
            
            # Trial conversion rate
            trial_users = await session.scalar(
                select(func.count(Subscription.id))
                .where(
                    and_(
                        Subscription.is_trial == True,
                        Subscription.created_at >= thirty_days_ago
                    )
                )
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
            
            metrics = {
                "active_users": active_users,
                "churn_rate": (churned_users / max(active_users, 1)) * 100,
                "trial_conversion_rate": (converted_trials / max(trial_users, 1)) * 100,
                "calculated_at": now.isoformat()
            }
            
            logger.info(f"User metrics: {metrics}")
            return metrics
            
    except Exception as e:
        logger.error(f"Error calculating user metrics: {e}")
        raise
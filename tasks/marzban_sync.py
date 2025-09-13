from celery import shared_task
from database.connection import async_session_maker
from database.models import User, Subscription, VPNConfig, SubscriptionStatus
from services.marzban import marzban_client, UserStatus
from sqlalchemy import select, and_
from datetime import datetime, timezone, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_subscriptions_from_marzban(self):
    """Sync subscription data from Marzban server"""
    return asyncio.run(_sync_subscriptions_from_marzban())


async def _sync_subscriptions_from_marzban():
    """Sync subscription expiration dates and status from Marzban"""
    try:
        async with async_session_maker() as session:
            # Get all VPN configs with active/trial subscriptions
            result = await session.execute(
                select(VPNConfig, User, Subscription)
                .join(User, VPNConfig.user_id == User.id)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        VPNConfig.is_active == True,
                        VPNConfig.marzban_user_id.isnot(None),
                        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                    )
                )
            )
            
            configs_to_sync = result.all()
            synced_count = 0
            errors_count = 0
            
            async with marzban_client as client:
                for vpn_config, user, subscription in configs_to_sync:
                    try:
                        # Get user data from Marzban
                        marzban_user = await client.get_user(vpn_config.marzban_user_id)
                        
                        if not marzban_user:
                            logger.warning(f"User {vpn_config.marzban_user_id} not found in Marzban")
                            continue
                        
                        # Check if Marzban user is expired or disabled
                        if marzban_user.status in [UserStatus.EXPIRED, UserStatus.DISABLED]:
                            if subscription.status != SubscriptionStatus.EXPIRED:
                                logger.info(f"Marking subscription as expired for user {user.telegram_id}")
                                subscription.status = SubscriptionStatus.EXPIRED
                                vpn_config.is_active = False
                        
                        # Sync expiration date from Marzban
                        if marzban_user.expire:
                            # Convert to naive datetime (PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
                            marzban_expire_date = datetime.fromtimestamp(marzban_user.expire, timezone.utc).replace(tzinfo=None)
                            
                            # Update subscription end_date if different
                            if subscription.end_date != marzban_expire_date:
                                logger.info(
                                    f"Updating subscription end_date for user {user.telegram_id}: "
                                    f"{subscription.end_date} -> {marzban_expire_date}"
                                )
                                subscription.end_date = marzban_expire_date
                        
                        # Sync traffic usage
                        if hasattr(marzban_user, 'used_traffic') and marzban_user.used_traffic:
                            vpn_config.traffic_used = marzban_user.used_traffic
                        
                        # Update last connected time (naive datetime for PostgreSQL)
                        vpn_config.last_connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        
                        synced_count += 1
                        
                        # Small delay to avoid overwhelming Marzban API
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error syncing user {user.telegram_id}: {e}")
                        errors_count += 1
                        continue
            
            await session.commit()
            logger.info(f"Marzban sync completed: {synced_count} synced, {errors_count} errors")
            
            return {
                'synced': synced_count,
                'errors': errors_count,
                'total': len(configs_to_sync)
            }
            
    except Exception as e:
        logger.error(f"Error in sync_subscriptions_from_marzban: {e}")
        raise


@shared_task(bind=True)  
def sync_user_status_from_marzban(self):
    """Sync user status from Marzban server"""
    return asyncio.run(_sync_user_status_from_marzban())


async def _sync_user_status_from_marzban():
    """Check and update user status based on Marzban data"""
    try:
        async with async_session_maker() as session:
            # Get all users with VPN configs
            result = await session.execute(
                select(VPNConfig, User)
                .join(User, VPNConfig.user_id == User.id)
                .where(VPNConfig.marzban_user_id.isnot(None))
            )
            
            configs = result.all()
            updated_count = 0
            
            async with marzban_client as client:
                for vpn_config, user in configs:
                    try:
                        # Get user data from Marzban
                        marzban_user = await client.get_user(vpn_config.marzban_user_id)
                        
                        if not marzban_user:
                            # User not found in Marzban - mark as inactive
                            if vpn_config.is_active:
                                vpn_config.is_active = False
                                logger.info(f"Marked VPN config inactive for missing user {user.telegram_id}")
                                updated_count += 1
                            continue
                        
                        # Update VPN config based on Marzban status
                        should_be_active = marzban_user.status == UserStatus.ACTIVE
                        
                        if vpn_config.is_active != should_be_active:
                            vpn_config.is_active = should_be_active
                            logger.info(f"Updated VPN status for user {user.telegram_id}: {should_be_active}")
                            updated_count += 1
                        
                        # Update traffic data
                        if hasattr(marzban_user, 'used_traffic'):
                            vpn_config.traffic_used = marzban_user.used_traffic or 0
                        
                        await asyncio.sleep(0.05)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Error checking status for user {user.telegram_id}: {e}")
                        continue
            
            await session.commit()
            logger.info(f"User status sync completed: {updated_count} users updated")
            
            return {'updated': updated_count, 'total': len(configs)}
            
    except Exception as e:
        logger.error(f"Error in sync_user_status_from_marzban: {e}")
        raise


@shared_task(bind=True)
def cleanup_expired_marzban_users(self):
    """Clean up expired users in Marzban"""
    return asyncio.run(_cleanup_expired_marzban_users())


async def _cleanup_expired_marzban_users():
    """Remove expired users from Marzban to free up resources"""
    try:
        async with async_session_maker() as session:
            # Get expired subscriptions with Marzban configs
            expired_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).replace(tzinfo=None)  # Keep for 7 days after expiry
            
            result = await session.execute(
                select(VPNConfig, User, Subscription)
                .join(User, VPNConfig.user_id == User.id)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        VPNConfig.marzban_user_id.isnot(None),
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        Subscription.end_date < expired_cutoff
                    )
                )
            )
            
            expired_configs = result.all()
            cleaned_count = 0
            
            async with marzban_client as client:
                for vpn_config, user, subscription in expired_configs:
                    try:
                        # Delete user from Marzban
                        success = await client.delete_user(vpn_config.marzban_user_id)
                        
                        if success:
                            # Mark config as deleted
                            vpn_config.marzban_user_id = None
                            vpn_config.is_active = False
                            cleaned_count += 1
                            
                            logger.info(f"Cleaned up expired Marzban user for {user.telegram_id}")
                        
                        await asyncio.sleep(0.1)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Error cleaning up user {user.telegram_id}: {e}")
                        continue
            
            await session.commit()
            logger.info(f"Marzban cleanup completed: {cleaned_count} users cleaned")
            
            return {'cleaned': cleaned_count, 'total': len(expired_configs)}
            
    except Exception as e:
        logger.error(f"Error in cleanup_expired_marzban_users: {e}")
        raise


@shared_task(bind=True)
def get_marzban_system_stats(self):
    """Get system statistics from Marzban"""
    return asyncio.run(_get_marzban_system_stats())


async def _get_marzban_system_stats():
    """Collect system stats from Marzban for monitoring"""
    try:
        async with marzban_client as client:
            stats = await client.get_system_stats()
            
            logger.info(f"Marzban system stats: {stats}")
            
            # Store in database for monitoring (could extend to save to DB)
            return {
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'stats': stats.dict() if hasattr(stats, 'dict') else stats
            }
            
    except Exception as e:
        logger.error(f"Error getting Marzban system stats: {e}")
        raise
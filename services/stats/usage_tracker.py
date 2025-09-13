import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, and_, text, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.models import UsageStat as UsageStats, VPNConfig, User
from services.marzban.client import MarzbanClient

logger = logging.getLogger(__name__)


class UsageTracker:
    """Service for tracking VPN usage statistics"""
    
    def __init__(self):
        self.marzban_client = MarzbanClient()
    
    async def update_user_usage(
        self, 
        session: AsyncSession,
        user_id: int,
        date: date = None
    ) -> bool:
        """Update usage statistics for a specific user"""
        try:
            if date is None:
                date = date.today()
            
            # Get user's VPN config
            vpn_config_result = await session.execute(
                select(VPNConfig).where(
                    and_(
                        VPNConfig.user_id == user_id,
                        VPNConfig.is_active == True
                    )
                )
            )
            vpn_config = vpn_config_result.scalar_one_or_none()
            
            if not vpn_config or not vpn_config.marzban_user_id:
                logger.debug(f"No active VPN config for user {user_id}")
                return False
            
            # Get usage data from Marzban
            async with self.marzban_client as client:
                usage_data = await client.get_user_usage(vpn_config.marzban_user_id)
            
            if not usage_data:
                logger.warning(f"No usage data from Marzban for user {user_id}")
                return False
            
            # Update or create usage statistics
            await self._upsert_usage_stats(
                session=session,
                user_id=user_id,
                date=date,
                usage_data=usage_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating usage for user {user_id}: {e}")
            return False
    
    async def update_all_users_usage(
        self, 
        session: AsyncSession,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Update usage statistics for all active users"""
        results = {'success': 0, 'failed': 0}
        
        try:
            # Get all users with active VPN configs
            active_users_result = await session.execute(
                select(VPNConfig.user_id).where(VPNConfig.is_active == True)
            )
            active_user_ids = [row[0] for row in active_users_result]
            
            # Process users in batches
            for i in range(0, len(active_user_ids), batch_size):
                batch = active_user_ids[i:i + batch_size]
                tasks = []
                
                for user_id in batch:
                    task = self.update_user_usage(session, user_id)
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        results['failed'] += 1
                    elif result:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            await session.commit()
            logger.info(f"Usage update results: {results}")
            
        except Exception as e:
            logger.error(f"Error in bulk usage update: {e}")
            await session.rollback()
        
        return results
    
    async def _upsert_usage_stats(
        self,
        session: AsyncSession,
        user_id: int,
        date: date,
        usage_data: Dict[str, Any]
    ):
        """Insert or update usage statistics"""
        try:
            # Prepare data
            usage_record = {
                'user_id': user_id,
                'date': date,
                'bytes_uploaded': usage_data.get('uploaded', 0),
                'bytes_downloaded': usage_data.get('downloaded', 0),
                'connections_count': usage_data.get('connections', 0),
                'unique_ips': usage_data.get('unique_ips', []),
                'created_at': datetime.utcnow()
            }
            
            # Use PostgreSQL UPSERT
            stmt = pg_insert(UsageStats.__table__).values(**usage_record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id', 'date'],
                set_=dict(
                    bytes_uploaded=stmt.excluded.bytes_uploaded,
                    bytes_downloaded=stmt.excluded.bytes_downloaded,
                    connections_count=stmt.excluded.connections_count,
                    unique_ips=stmt.excluded.unique_ips,
                    created_at=datetime.utcnow()
                )
            )
            
            await session.execute(stmt)
            
        except Exception as e:
            logger.error(f"Error upserting usage stats for user {user_id}: {e}")
            raise
    
    async def get_user_usage_summary(
        self,
        session: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage summary for a user"""
        try:
            start_date = date.today() - timedelta(days=days)
            
            result = await session.execute(
                select(UsageStats).where(
                    and_(
                        UsageStats.user_id == user_id,
                        UsageStats.date >= start_date
                    )
                ).order_by(UsageStats.date.desc())
            )
            
            usage_records = result.scalars().all()
            
            if not usage_records:
                return {
                    'total_uploaded': 0,
                    'total_downloaded': 0,
                    'total_data': 0,
                    'average_daily': 0,
                    'days_active': 0,
                    'last_activity': None
                }
            
            total_uploaded = sum(r.bytes_uploaded or 0 for r in usage_records)
            total_downloaded = sum(r.bytes_downloaded or 0 for r in usage_records)
            total_data = total_uploaded + total_downloaded
            
            days_with_activity = len([r for r in usage_records if (r.bytes_uploaded or 0) + (r.bytes_downloaded or 0) > 0])
            average_daily = total_data / days if days > 0 else 0
            
            last_activity = max(r.date for r in usage_records if (r.bytes_uploaded or 0) + (r.bytes_downloaded or 0) > 0) if usage_records else None
            
            return {
                'total_uploaded': total_uploaded,
                'total_downloaded': total_downloaded,
                'total_data': total_data,
                'total_data_gb': round(total_data / (1024**3), 2),
                'average_daily_gb': round(average_daily / (1024**3), 2),
                'days_active': days_with_activity,
                'last_activity': last_activity
            }
            
        except Exception as e:
            logger.error(f"Error getting usage summary for user {user_id}: {e}")
            return {}
    
    async def get_usage_chart_data(
        self,
        session: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get usage data for chart visualization"""
        try:
            start_date = date.today() - timedelta(days=days)
            
            result = await session.execute(
                select(UsageStats).where(
                    and_(
                        UsageStats.user_id == user_id,
                        UsageStats.date >= start_date
                    )
                ).order_by(UsageStats.date)
            )
            
            usage_records = result.scalars().all()
            
            chart_data = []
            for record in usage_records:
                chart_data.append({
                    'date': record.date.strftime('%Y-%m-%d'),
                    'uploaded_gb': round((record.bytes_uploaded or 0) / (1024**3), 2),
                    'downloaded_gb': round((record.bytes_downloaded or 0) / (1024**3), 2),
                    'total_gb': round(((record.bytes_uploaded or 0) + (record.bytes_downloaded or 0)) / (1024**3), 2),
                    'connections': record.connections_count or 0
                })
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error getting chart data for user {user_id}: {e}")
            return []
    
    async def get_top_users_by_usage(
        self,
        session: AsyncSession,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top users by data usage"""
        try:
            start_date = date.today() - timedelta(days=days)
            
            result = await session.execute(
                select(
                    UsageStats.user_id,
                    func.sum(UsageStats.bytes_uploaded + UsageStats.bytes_downloaded).label('total_usage')
                ).where(
                    UsageStats.date >= start_date
                ).group_by(
                    UsageStats.user_id
                ).order_by(
                    text('total_usage DESC')
                ).limit(limit)
            )
            
            usage_data = result.all()
            
            # Get user information
            top_users = []
            for row in usage_data:
                user_result = await session.execute(
                    select(User).where(User.id == row.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    top_users.append({
                        'user_id': row.user_id,
                        'username': user.username or f'User_{user.telegram_id}',
                        'total_usage_gb': round(row.total_usage / (1024**3), 2)
                    })
            
            return top_users
            
        except Exception as e:
            logger.error(f"Error getting top users by usage: {e}")
            return []
    
    async def cleanup_old_usage_data(
        self,
        session: AsyncSession,
        keep_days: int = 365
    ) -> int:
        """Clean up old usage data"""
        try:
            cutoff_date = date.today() - timedelta(days=keep_days)
            
            result = await session.execute(
                select(func.count(UsageStats.id)).where(
                    UsageStats.date < cutoff_date
                )
            )
            records_to_delete = result.scalar()
            
            if records_to_delete > 0:
                await session.execute(
                    UsageStats.__table__.delete().where(
                        UsageStats.date < cutoff_date
                    )
                )
                await session.commit()
                logger.info(f"Cleaned up {records_to_delete} old usage records")
            
            return records_to_delete
            
        except Exception as e:
            logger.error(f"Error cleaning up old usage data: {e}")
            await session.rollback()
            return 0
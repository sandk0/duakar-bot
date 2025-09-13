from celery import shared_task
from database.connection import async_session_maker
from database.models import ActionLog, Payment, BroadcastMessage
from sqlalchemy import select, delete, and_
from datetime import datetime, timedelta
from bot.config import settings
import logging
import subprocess
import os
import asyncio

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def backup_database(self):
    """Create database backup"""
    return asyncio.run(_backup_database())


async def _backup_database():
    """Async implementation of database backup"""
    try:
        # Parse database URL
        db_url = settings.database_url
        # Remove asyncpg prefix for pg_dump
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"vpn_bot_backup_{timestamp}.sql"
        backup_path = f"/app/backups/{backup_filename}"
        
        # Create backups directory if it doesn't exist
        os.makedirs("/app/backups", exist_ok=True)
        
        # Run pg_dump
        cmd = [
            "pg_dump",
            db_url,
            "--no-password",
            "--verbose",
            "--file", backup_path
        ]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if process.returncode == 0:
            # Get file size
            file_size = os.path.getsize(backup_path)
            logger.info(f"Database backup created: {backup_filename} ({file_size} bytes)")
            
            # Cleanup old backups (keep last 30)
            await _cleanup_old_backups("/app/backups", 30)
            
            return {
                "status": "success",
                "filename": backup_filename,
                "size": file_size
            }
        else:
            logger.error(f"Database backup failed: {process.stderr}")
            return {
                "status": "failed",
                "error": process.stderr
            }
    
    except subprocess.TimeoutExpired:
        logger.error("Database backup timed out")
        return {"status": "failed", "error": "Timeout"}
    
    except Exception as e:
        logger.error(f"Error in backup_database: {e}")
        return {"status": "failed", "error": str(e)}


async def _cleanup_old_backups(backup_dir: str, keep_count: int):
    """Clean up old backup files"""
    try:
        if not os.path.exists(backup_dir):
            return
        
        # Get all backup files
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("vpn_bot_backup_") and filename.endswith(".sql"):
                filepath = os.path.join(backup_dir, filename)
                mtime = os.path.getmtime(filepath)
                backup_files.append((filepath, mtime))
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old backups
        files_to_remove = backup_files[keep_count:]
        for filepath, _ in files_to_remove:
            try:
                os.remove(filepath)
                logger.info(f"Removed old backup: {os.path.basename(filepath)}")
            except Exception as e:
                logger.error(f"Error removing backup {filepath}: {e}")
    
    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")


@shared_task(bind=True)
def cleanup_expired_data(self):
    """Clean up expired data from database"""
    return asyncio.run(_cleanup_expired_data())


async def _cleanup_expired_data():
    """Async implementation of data cleanup"""
    try:
        async with async_session_maker() as session:
            now = datetime.now()
            cleanup_stats = {
                "action_logs": 0,
                "old_payments": 0,
                "broadcast_messages": 0
            }
            
            # Clean up action logs older than 30 days
            thirty_days_ago = now - timedelta(days=30)
            result = await session.execute(
                delete(ActionLog)
                .where(ActionLog.created_at < thirty_days_ago)
            )
            cleanup_stats["action_logs"] = result.rowcount
            
            # Clean up old failed payments (older than 90 days)
            ninety_days_ago = now - timedelta(days=90)
            result = await session.execute(
                delete(Payment)
                .where(
                    and_(
                        Payment.status.in_(["failed", "cancelled"]),
                        Payment.created_at < ninety_days_ago
                    )
                )
            )
            cleanup_stats["old_payments"] = result.rowcount
            
            # Clean up old broadcast messages (older than 60 days)
            sixty_days_ago = now - timedelta(days=60)
            result = await session.execute(
                delete(BroadcastMessage)
                .where(BroadcastMessage.created_at < sixty_days_ago)
            )
            cleanup_stats["broadcast_messages"] = result.rowcount
            
            await session.commit()
            
            logger.info(f"Data cleanup completed: {cleanup_stats}")
            return cleanup_stats
    
    except Exception as e:
        logger.error(f"Error in cleanup_expired_data: {e}")
        raise


@shared_task(bind=True)
def export_user_data(self, format: str = "csv"):
    """Export user data for admin"""
    return asyncio.run(_export_user_data(format))


async def _export_user_data(format: str):
    """Async implementation of user data export"""
    try:
        async with async_session_maker() as session:
            from database.models import User, Subscription, VPNConfig
            
            # Get all users with their latest subscription
            result = await session.execute(
                select(User, Subscription, VPNConfig)
                .outerjoin(
                    Subscription,
                    and_(
                        User.id == Subscription.user_id,
                        Subscription.id == (
                            select(Subscription.id)
                            .where(Subscription.user_id == User.id)
                            .order_by(Subscription.created_at.desc())
                            .limit(1)
                            .scalar_subquery()
                        )
                    )
                )
                .outerjoin(VPNConfig, User.id == VPNConfig.user_id)
            )
            
            users_data = result.all()
            
            if format.lower() == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Headers
                writer.writerow([
                    "telegram_id", "username", "first_name", "last_name",
                    "registration_date", "is_blocked", "subscription_status",
                    "subscription_end", "has_vpn_config", "last_used"
                ])
                
                # Data
                for user, subscription, vpn_config in users_data:
                    writer.writerow([
                        user.telegram_id,
                        user.username or "",
                        user.first_name or "",
                        user.last_name or "",
                        user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "Yes" if user.is_blocked else "No",
                        subscription.status if subscription else "None",
                        subscription.end_date.strftime("%Y-%m-%d") if subscription and subscription.end_date else "",
                        "Yes" if vpn_config and vpn_config.is_active else "No",
                        vpn_config.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if vpn_config and vpn_config.last_used_at else ""
                    ])
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"users_export_{timestamp}.csv"
                filepath = f"/app/exports/{filename}"
                
                os.makedirs("/app/exports", exist_ok=True)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(output.getvalue())
                
                file_size = os.path.getsize(filepath)
                
                logger.info(f"User data exported: {filename} ({len(users_data)} records, {file_size} bytes)")
                
                return {
                    "status": "success",
                    "filename": filename,
                    "records": len(users_data),
                    "size": file_size
                }
            
            else:
                return {
                    "status": "failed",
                    "error": f"Unsupported format: {format}"
                }
    
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@shared_task(bind=True)
def cleanup_temp_files(self):
    """Clean up temporary files"""
    try:
        temp_dirs = ["/app/exports", "/app/temp"]
        cleaned_count = 0
        
        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
            
            # Remove files older than 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                
                if os.path.isfile(filepath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if mtime < cutoff_time:
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                            logger.debug(f"Removed temp file: {filename}")
                        except Exception as e:
                            logger.error(f"Error removing temp file {filepath}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return {"cleaned_files": cleaned_count}
    
    except Exception as e:
        logger.error(f"Error in cleanup_temp_files: {e}")
        raise
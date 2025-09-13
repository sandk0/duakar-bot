from celery import Celery
from celery.schedules import crontab
from bot.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('vpn_bot')

# Configure Celery
app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Task routes
app.conf.task_routes = {
    'tasks.notifications.*': {'queue': 'notifications'},
    'tasks.payments.*': {'queue': 'payments'},
    'tasks.stats.*': {'queue': 'stats'},
    'tasks.backup.*': {'queue': 'backup'},
}

# Periodic tasks schedule
app.conf.beat_schedule = {
    # Check expiring subscriptions every hour
    'check-expiring-subscriptions': {
        'task': 'tasks.notifications.check_expiring_subscriptions',
        'schedule': crontab(minute=0),  # Every hour
    },
    
    # Process failed payments every 6 hours
    'retry-failed-payments': {
        'task': 'tasks.payments.retry_failed_payments',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    
    # Collect usage stats daily at 3 AM
    'collect-daily-stats': {
        'task': 'tasks.stats.collect_daily_stats',
        'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
    },
    
    # Cleanup expired data weekly
    'cleanup-expired-data': {
        'task': 'tasks.backup.cleanup_expired_data',
        'schedule': crontab(minute=0, hour=4, day_of_week=0),  # Weekly on Sunday at 4 AM
    },
    
    # Backup database weekly
    'backup-database': {
        'task': 'tasks.backup.backup_database',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Weekly on Sunday at 2 AM
    },
    
    # Update VPN usage stats every 30 minutes
    'sync-vpn-usage': {
        'task': 'tasks.stats.sync_vpn_usage',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Check server health every 5 minutes
    'check-server-health': {
        'task': 'tasks.stats.check_server_health',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

# Auto-discover tasks
app.autodiscover_tasks([
    'tasks.notifications',
    'tasks.payments', 
    'tasks.stats',
    'tasks.backup'
])

if __name__ == '__main__':
    app.start()
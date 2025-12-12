import logging
from datetime import datetime, timedelta
from backend.database import get_database

logger = logging.getLogger(__name__)


async def cleanup_old_sessions():
    """
    Clean up old channel sessions
    Removes sessions older than 30 days
    """
    try:
        db = get_database()
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        result = await db.channel_sessions.delete_many({
            "created_at": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} old sessions")
    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {e}")


async def cleanup_revoked_tokens():
    """
    Clean up expired revoked tokens
    MongoDB TTL index handles this, but this is a backup
    """
    try:
        db = get_database()
        now = datetime.utcnow()
        
        result = await db.revoked_tokens.delete_many({
            "expires_at": {"$lt": now}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} expired tokens")
    except Exception as e:
        logger.error(f"Error cleaning up revoked tokens: {e}")


async def cleanup_abandoned_carts():
    """
    Clean up abandoned carts older than 7 days
    """
    try:
        db = get_database()
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        result = await db.carts.delete_many({
            "updated_at": {"$lt": cutoff_date},
            "items": {"$size": 0}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} abandoned carts")
    except Exception as e:
        logger.error(f"Error cleaning up abandoned carts: {e}")


async def run_daily_cleanup():
    """
    Run all cleanup tasks
    Called by scheduler once per day
    """
    logger.info("Starting daily cleanup tasks")
    await cleanup_old_sessions()
    await cleanup_revoked_tokens()
    await cleanup_abandoned_carts()
    logger.info("Daily cleanup tasks completed")

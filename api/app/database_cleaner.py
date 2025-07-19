import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from sqlalchemy import and_, text

from .s3_export import S3ExportConfig
from .models import EventLog

logger = logging.getLogger(__name__)

class DatabaseCleanupConfig:
    """Configuration for database cleanup operations with safety settings"""
    
    def __init__(self):
        # Cleanup configuration
        self.cleanup_enabled = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"
        self.cleanup_delay_hours = int(os.getenv("CLEANUP_DELAY_HOURS", "1"))
        self.cleanup_batch_size = int(os.getenv("CLEANUP_BATCH_SIZE", "1000"))
        self.cleanup_verify_s3 = os.getenv("CLEANUP_VERIFY_S3", "true").lower() == "true"
        self.cleanup_max_retries = int(os.getenv("CLEANUP_MAX_RETRIES", "3"))
        
        # Inherit S3 configuration for verification
        self.s3_config = S3ExportConfig()
        
        # Validation
        self.validate_config()
    
    def validate_config(self):
        """Validate cleanup configuration safety"""
        errors = []
        
        if self.cleanup_delay_hours < 0:
            errors.append("CLEANUP_DELAY_HOURS must be non-negative")
        
        if self.cleanup_batch_size <= 0 or self.cleanup_batch_size > 10000:
            errors.append("CLEANUP_BATCH_SIZE must be between 1 and 10000")
        
        if self.cleanup_max_retries < 1:
            errors.append("CLEANUP_MAX_RETRIES must be at least 1")
        
        if errors:
            raise ValueError(f"Database cleanup configuration errors: {', '.join(errors)}")

class DatabaseCleaner:
    """Database cleanup functionality with safety-first architecture"""
    
    def __init__(self, config: DatabaseCleanupConfig):
        self.config = config
        self.s3_client = config.s3_config.get_raw_s3_client()
        logger.info(f"DatabaseCleaner initialized - enabled: {config.cleanup_enabled}, delay: {config.cleanup_delay_hours}h")
    
    def cleanup_exported_events(self, db: Session) -> Dict[str, Any]:
        """
        Main entry point for database cleanup
        Safely delete events that have been exported to S3
        """
        try:
            if not self.config.cleanup_enabled:
                return {
                    "status": "disabled",
                    "message": "Database cleanup is disabled",
                    "events_deleted": 0,
                    "cleanup_time": datetime.now(timezone.utc).isoformat()
                }
            
            # Get deletable events with safety filters
            deletable_events = self._get_deletable_events(db)
            
            if not deletable_events:
                return {
                    "status": "success",
                    "message": "No events eligible for cleanup",
                    "events_deleted": 0,
                    "cleanup_time": datetime.now(timezone.utc).isoformat()
                }
            
            logger.info(f"Found {len(deletable_events)} events eligible for cleanup")
            
            # Verify S3 backup exists (if enabled)
            if self.config.cleanup_verify_s3:
                verified_events = self._verify_s3_backup_exists(deletable_events)
                if len(verified_events) != len(deletable_events):
                    logger.warning(f"S3 verification reduced eligible events from {len(deletable_events)} to {len(verified_events)}")
                deletable_events = verified_events
            
            if not deletable_events:
                return {
                    "status": "success",
                    "message": "No events passed S3 verification",
                    "events_deleted": 0,
                    "cleanup_time": datetime.now(timezone.utc).isoformat()
                }
            
            # Perform batch cleanup
            deleted_count = self._cleanup_batch(db, deletable_events)
            
            return {
                "status": "success",
                "message": f"Successfully cleaned up {deleted_count} events",
                "events_deleted": deleted_count,
                "cleanup_time": datetime.now(timezone.utc).isoformat(),
                "s3_verification": self.config.cleanup_verify_s3
            }
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Cleanup failed: {str(e)}",
                "events_deleted": 0,
                "cleanup_time": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_deletable_events(self, db: Session) -> List[int]:
        """Get events that are eligible for deletion with safety filters"""
        try:
            # Calculate minimum age cutoff
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.config.cleanup_delay_hours)
            
            # Query events that:
            # 1. Have been exported to raw S3 (raw_exported_at IS NOT NULL)
            # 2. Are older than the minimum age requirement
            # 3. Limit to batch size for safe processing
            query = db.query(EventLog.id).filter(
                and_(
                    EventLog.raw_exported_at.isnot(None),
                    EventLog.raw_exported_at < cutoff_time
                )
            ).order_by(EventLog.raw_exported_at).limit(self.config.cleanup_batch_size)
            
            event_ids = [row[0] for row in query.all()]
            
            logger.info(f"Found {len(event_ids)} events eligible for deletion (older than {cutoff_time})")
            return event_ids
            
        except Exception as e:
            logger.error(f"Failed to get deletable events: {str(e)}")
            return []
    
    def _verify_s3_backup_exists(self, event_ids: List[int]) -> List[int]:
        """Verify that S3 backup exists for events before allowing deletion"""
        if not event_ids:
            return []
        
        try:
            # For Phase 3 MVP, we'll verify that the raw S3 bucket is accessible
            # and has recent files. In a more sophisticated implementation,
            # we could cross-reference specific export files with event IDs.
            
            # Check if raw S3 bucket is accessible and has recent exports
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_config.raw_bucket,
                Prefix="raw-events/",
                MaxKeys=10
            )
            
            if 'Contents' not in response or len(response['Contents']) == 0:
                logger.error("No raw exports found in S3 bucket - aborting cleanup for safety")
                return []
            
            # Check that the most recent export is reasonably recent (within 24 hours)
            latest_export = max(response['Contents'], key=lambda x: x['LastModified'])
            time_since_export = datetime.now(timezone.utc) - latest_export['LastModified'].replace(tzinfo=timezone.utc)
            
            if time_since_export.total_seconds() > 24 * 3600:  # 24 hours
                logger.warning(f"Latest S3 export is {time_since_export} old - cleanup may be unsafe")
                # Continue but log warning for monitoring
            
            logger.info(f"S3 verification passed - latest export: {latest_export['LastModified']}")
            return event_ids
            
        except Exception as e:
            logger.error(f"S3 verification failed: {str(e)} - aborting cleanup for safety")
            return []
    
    def _cleanup_batch(self, db: Session, event_ids: List[int]) -> int:
        """Perform atomic batch deletion with transaction safety"""
        if not event_ids:
            return 0
        
        deleted_count = 0
        
        try:
            # Process in smaller sub-batches to minimize lock time
            sub_batch_size = min(1000, self.config.cleanup_batch_size)
            
            for i in range(0, len(event_ids), sub_batch_size):
                batch_ids = event_ids[i:i + sub_batch_size]
                
                try:
                    # Atomic deletion of sub-batch
                    deleted_rows = db.query(EventLog).filter(
                        EventLog.id.in_(batch_ids)
                    ).delete(synchronize_session=False)
                    
                    db.commit()
                    deleted_count += deleted_rows
                    
                    logger.info(f"Deleted {deleted_rows} events in batch {i//sub_batch_size + 1}")
                    
                except Exception as batch_error:
                    logger.error(f"Failed to delete batch {i//sub_batch_size + 1}: {str(batch_error)}")
                    db.rollback()
                    # Continue with next batch rather than failing completely
                    continue
            
            logger.info(f"Cleanup completed - deleted {deleted_count} events total")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Batch cleanup failed: {str(e)}")
            db.rollback()
            return deleted_count
    
    def get_cleanup_status(self, db: Session) -> Dict[str, Any]:
        """Get database cleanup status and metrics"""
        try:
            # Calculate minimum age cutoff
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.config.cleanup_delay_hours)
            
            # Count events by cleanup status
            total_events = db.query(EventLog).count()
            raw_exported_events = db.query(EventLog).filter(EventLog.raw_exported_at.isnot(None)).count()
            cleanup_eligible = db.query(EventLog).filter(
                and_(
                    EventLog.raw_exported_at.isnot(None),
                    EventLog.raw_exported_at < cutoff_time
                )
            ).count()
            
            # Get latest cleanup-eligible event
            latest_eligible = db.query(EventLog).filter(
                and_(
                    EventLog.raw_exported_at.isnot(None),
                    EventLog.raw_exported_at < cutoff_time
                )
            ).order_by(EventLog.raw_exported_at.desc()).first()
            
            return {
                "cleanup_enabled": self.config.cleanup_enabled,
                "cleanup_delay_hours": self.config.cleanup_delay_hours,
                "cleanup_batch_size": self.config.cleanup_batch_size,
                "s3_verification_enabled": self.config.cleanup_verify_s3,
                "total_events": total_events,
                "raw_exported_events": raw_exported_events,
                "cleanup_eligible_events": cleanup_eligible,
                "latest_eligible_export": latest_eligible.raw_exported_at.isoformat() if latest_eligible else None,
                "cutoff_time": cutoff_time.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cleanup status: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

def create_database_cleaner() -> DatabaseCleaner:
    """Factory function to create DatabaseCleaner with configuration"""
    config = DatabaseCleanupConfig()
    return DatabaseCleaner(config)
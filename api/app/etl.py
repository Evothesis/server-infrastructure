"""
ETL API endpoints for processing raw events into analytics tables
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date, timedelta
import logging
from typing import List, Dict, Any

from .database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["ETL"])

@router.post("/run")
async def run_etl_pipeline(
    background_tasks: BackgroundTasks,
    batch_size: int = 1000,
    db: Session = Depends(get_db)
):
    """
    Run the complete ETL pipeline to process raw events into analytics tables
    """
    try:
        # Run ETL in background
        background_tasks.add_task(execute_etl_pipeline, batch_size)
        
        return {
            "status": "started",
            "message": f"ETL pipeline started with batch size {batch_size}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting ETL pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to start ETL pipeline")

@router.post("/run-sync")
async def run_etl_pipeline_sync(
    batch_size: int = 1000,
    db: Session = Depends(get_db)
):
    """
    Run the ETL pipeline synchronously and return results
    """
    try:
        results = []
        
        # Execute the ETL pipeline
        result = db.execute(text("SELECT * FROM run_etl_pipeline(:batch_size)"), {"batch_size": batch_size})
        
        for row in result:
            results.append({
                "step_name": row[0],
                "records_processed": row[1],
                "execution_time": str(row[2])
            })
        
        db.commit()
        
        total_processed = sum(r["records_processed"] for r in results)
        
        return {
            "status": "completed",
            "total_records_processed": total_processed,
            "steps": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error running ETL pipeline: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"ETL pipeline failed: {str(e)}")

@router.post("/process/{event_type}")
async def process_specific_event_type(
    event_type: str,
    batch_size: int = 1000,
    db: Session = Depends(get_db)
):
    """
    Process specific event type only
    """
    try:
        function_map = {
            "pageview": "process_pageview_events",
            "page_exit": "process_page_exit_events", 
            "batch": "process_batch_events",
            "form_submit": "process_form_submit_events"
        }
        
        if event_type not in function_map:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown event type. Supported: {list(function_map.keys())}"
            )
        
        function_name = function_map[event_type]
        result = db.execute(
            text(f"SELECT {function_name}(:batch_size)"), 
            {"batch_size": batch_size}
        )
        
        processed_count = result.scalar()
        db.commit()
        
        return {
            "status": "completed",
            "event_type": event_type,
            "records_processed": processed_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing {event_type} events: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process {event_type} events")

@router.post("/calculate-daily-metrics")
async def calculate_daily_metrics(
    target_date: date = None,
    db: Session = Depends(get_db)
):
    """
    Calculate daily metrics for a specific date (defaults to yesterday)
    """
    try:
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        result = db.execute(
            text("SELECT calculate_daily_metrics(:target_date)"), 
            {"target_date": target_date}
        )
        
        sites_processed = result.scalar()
        db.commit()
        
        return {
            "status": "completed",
            "target_date": target_date.isoformat(),
            "sites_processed": sites_processed,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating daily metrics: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to calculate daily metrics")

@router.post("/cleanup")
async def cleanup_old_data(
    retention_days: int = 90,
    cleanup_metrics: bool = False,
    metrics_retention_days: int = 365,
    db: Session = Depends(get_db)
):
    """
    Clean up old processed events and optionally old metrics
    """
    try:
        # Cleanup processed events
        result = db.execute(
            text("SELECT cleanup_processed_events(:retention_days)"), 
            {"retention_days": retention_days}
        )
        events_deleted = result.scalar()
        
        metrics_deleted = 0
        if cleanup_metrics:
            result = db.execute(
                text("SELECT cleanup_old_metrics(:retention_days)"), 
                {"retention_days": metrics_retention_days}
            )
            metrics_deleted = result.scalar()
        
        db.commit()
        
        return {
            "status": "completed",
            "events_deleted": events_deleted,
            "metrics_deleted": metrics_deleted,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/status")
async def get_etl_status(db: Session = Depends(get_db)):
    """
    Get ETL processing status and statistics
    """
    try:
        # Get unprocessed event counts by type
        unprocessed_query = text("""
            SELECT 
                event_type,
                COUNT(*) as unprocessed_count,
                MIN(created_at) as oldest_unprocessed,
                MAX(created_at) as newest_unprocessed
            FROM events_log 
            WHERE processed_at IS NULL
            GROUP BY event_type
            ORDER BY unprocessed_count DESC
        """)
        
        unprocessed_result = db.execute(unprocessed_query)
        unprocessed_events = []
        
        for row in unprocessed_result:
            unprocessed_events.append({
                "event_type": row[0],
                "count": row[1],
                "oldest": row[2].isoformat() if row[2] else None,
                "newest": row[3].isoformat() if row[3] else None
            })
        
        # Get analytics table counts
        analytics_query = text("""
            SELECT 
                'user_sessions' as table_name, COUNT(*) as record_count
            FROM user_sessions
            UNION ALL
            SELECT 'pageviews', COUNT(*) FROM pageviews
            UNION ALL
            SELECT 'user_events', COUNT(*) FROM user_events
            UNION ALL
            SELECT 'form_submissions', COUNT(*) FROM form_submissions
            UNION ALL
            SELECT 'daily_site_metrics', COUNT(*) FROM daily_site_metrics
            ORDER BY table_name
        """)
        
        analytics_result = db.execute(analytics_query)
        analytics_counts = {}
        
        for row in analytics_result:
            analytics_counts[row[0]] = row[1]
        
        # Get latest daily metrics date
        latest_metrics_query = text("""
            SELECT MAX(metric_date) as latest_date
            FROM daily_site_metrics
        """)
        
        latest_metrics_result = db.execute(latest_metrics_query)
        latest_metrics_date = latest_metrics_result.scalar()
        
        return {
            "status": "healthy",
            "unprocessed_events": unprocessed_events,
            "analytics_table_counts": analytics_counts,
            "latest_daily_metrics_date": latest_metrics_date.isoformat() if latest_metrics_date else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ETL status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ETL status")

@router.get("/recent-sessions")
async def get_recent_sessions(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent sessions from analytics tables (for testing)
    """
    try:
        query = text("""
            SELECT 
                session_id,
                visitor_id,
                site_id,
                session_start,
                session_end,
                duration_seconds,
                pageview_count,
                event_count,
                bounce,
                entry_path,
                exit_path,
                utm_source,
                utm_medium,
                utm_campaign,
                referrer_type
            FROM user_sessions
            ORDER BY session_start DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        sessions = []
        
        for row in result:
            sessions.append({
                "session_id": row[0],
                "visitor_id": row[1],
                "site_id": row[2],
                "session_start": row[3].isoformat() if row[3] else None,
                "session_end": row[4].isoformat() if row[4] else None,
                "duration_seconds": row[5],
                "pageview_count": row[6],
                "event_count": row[7],
                "bounce": row[8],
                "entry_path": row[9],
                "exit_path": row[10],
                "utm_source": row[11],
                "utm_medium": row[12],
                "utm_campaign": row[13],
                "referrer_type": row[14]
            })
        
        return {
            "sessions": sessions,
            "count": len(sessions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent sessions")

# Background task function
def execute_etl_pipeline(batch_size: int):
    """
    Execute ETL pipeline in background
    """
    try:
        from .database import SessionLocal
        db = SessionLocal()
        
        logger.info(f"Starting background ETL pipeline with batch size {batch_size}")
        
        result = db.execute(text("SELECT * FROM run_etl_pipeline(:batch_size)"), {"batch_size": batch_size})
        
        total_processed = 0
        for row in result:
            step_name = row[0]
            records_processed = row[1]
            execution_time = row[2]
            total_processed += records_processed
            logger.info(f"ETL Step {step_name}: {records_processed} records in {execution_time}")
        
        db.commit()
        logger.info(f"Background ETL pipeline completed. Total records processed: {total_processed}")
        
    except Exception as e:
        logger.error(f"Background ETL pipeline failed: {e}")
        db.rollback()
    finally:
        db.close()
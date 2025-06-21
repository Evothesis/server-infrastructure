#!/usr/bin/env python3
"""
ETL Testing and Management Script

This script provides command-line tools for testing and running the ETL pipeline.
"""

import requests
import argparse
import json
import time
from datetime import datetime, date, timedelta

# API base URL
BASE_URL = "http://localhost:8000"

def test_etl_status():
    """Test ETL status endpoint"""
    print("🔍 Checking ETL status...")
    
    try:
        response = requests.get(f"{BASE_URL}/etl/status")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ ETL Status: {data['status']}")
        
        print("\n📊 Unprocessed Events:")
        for event in data['unprocessed_events']:
            print(f"  {event['event_type']}: {event['count']} events")
            if event['oldest']:
                print(f"    Oldest: {event['oldest']}")
        
        print("\n📈 Analytics Table Counts:")
        for table, count in data['analytics_table_counts'].items():
            print(f"  {table}: {count:,} records")
        
        if data['latest_daily_metrics_date']:
            print(f"\n📅 Latest Daily Metrics: {data['latest_daily_metrics_date']}")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error checking ETL status: {e}")
        return None

def run_etl_pipeline(sync=True, batch_size=1000):
    """Run the ETL pipeline"""
    print(f"🚀 Running ETL pipeline (batch_size={batch_size})...")
    
    endpoint = "/etl/run-sync" if sync else "/etl/run"
    
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            params={"batch_size": batch_size}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ ETL Status: {data['status']}")
        
        if sync and 'steps' in data:
            print(f"\n📊 Total Records Processed: {data['total_records_processed']}")
            print("\n🔄 ETL Steps:")
            for step in data['steps']:
                print(f"  {step['step_name']}: {step['records_processed']} records in {step['execution_time']}")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error running ETL pipeline: {e}")
        return None

def process_specific_event_type(event_type, batch_size=1000):
    """Process specific event type"""
    print(f"🔄 Processing {event_type} events (batch_size={batch_size})...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/etl/process/{event_type}",
            params={"batch_size": batch_size}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Processed {data['records_processed']} {event_type} events")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error processing {event_type} events: {e}")
        return None

def calculate_daily_metrics(target_date=None):
    """Calculate daily metrics"""
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    print(f"📊 Calculating daily metrics for {target_date}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/etl/calculate-daily-metrics",
            params={"target_date": target_date.isoformat()}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Processed metrics for {data['sites_processed']} sites")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error calculating daily metrics: {e}")
        return None

def cleanup_old_data(retention_days=90, cleanup_metrics=False):
    """Clean up old data"""
    print(f"🧹 Cleaning up data older than {retention_days} days...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/etl/cleanup",
            params={
                "retention_days": retention_days,
                "cleanup_metrics": cleanup_metrics
            }
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Deleted {data['events_deleted']} events")
        if cleanup_metrics:
            print(f"✅ Deleted {data['metrics_deleted']} metric records")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error during cleanup: {e}")
        return None

def get_recent_sessions(limit=10):
    """Get recent sessions"""
    print(f"👥 Getting {limit} recent sessions...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/etl/recent-sessions",
            params={"limit": limit}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Found {data['count']} sessions")
        
        print("\n📋 Recent Sessions:")
        for session in data['sessions']:
            print(f"  Session {session['session_id'][:8]}...")
            print(f"    Visitor: {session['visitor_id'][:8]}...")
            print(f"    Start: {session['session_start']}")
            print(f"    Pages: {session['pageview_count']}, Events: {session['event_count']}")
            print(f"    Entry: {session['entry_path']}")
            if session['utm_source']:
                print(f"    UTM: {session['utm_source']}/{session['utm_medium']}")
            print()
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error getting recent sessions: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="ETL Pipeline Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Check ETL status')
    
    # Run ETL command
    run_parser = subparsers.add_parser('run', help='Run ETL pipeline')
    run_parser.add_argument('--async', action='store_true', help='Run asynchronously')
    run_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size')
    
    # Process specific event type
    process_parser = subparsers.add_parser('process', help='Process specific event type')
    process_parser.add_argument('event_type', choices=['pageview', 'page_exit', 'batch', 'form_submit'])
    process_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size')
    
    # Calculate daily metrics
    metrics_parser = subparsers.add_parser('metrics', help='Calculate daily metrics')
    metrics_parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--retention-days', type=int, default=90, help='Retention period in days')
    cleanup_parser.add_argument('--cleanup-metrics', action='store_true', help='Also cleanup old metrics')
    
    # Sessions command
    sessions_parser = subparsers.add_parser('sessions', help='Get recent sessions')
    sessions_parser.add_argument('--limit', type=int, default=10, help='Number of sessions to show')
    
    # Full command - run complete ETL process
    full_parser = subparsers.add_parser('full', help='Run complete ETL process')
    full_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        test_etl_status()
    
    elif args.command == 'run':
        run_etl_pipeline(sync=not args.async, batch_size=args.batch_size)
    
    elif args.command == 'process':
        process_specific_event_type(args.event_type, args.batch_size)
    
    elif args.command == 'metrics':
        target_date = None
        if args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        calculate_daily_metrics(target_date)
    
    elif args.command == 'cleanup':
        cleanup_old_data(args.retention_days, args.cleanup_metrics)
    
    elif args.command == 'sessions':
        get_recent_sessions(args.limit)
    
    elif args.command == 'full':
        print("🚀 Running full ETL process...")
        print("\n1. Checking status...")
        test_etl_status()
        
        print("\n2. Running ETL pipeline...")
        run_etl_pipeline(sync=True, batch_size=args.batch_size)
        
        print("\n3. Calculating daily metrics...")
        calculate_daily_metrics()
        
        print("\n4. Final status check...")
        test_etl_status()
        
        print("\n5. Sample sessions...")
        get_recent_sessions(5)
        
        print("\n✅ Full ETL process completed!")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
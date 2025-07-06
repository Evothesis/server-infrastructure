#!/usr/bin/env python3
"""
System Monitoring Script for Evothesis Stress Testing
Monitors Docker containers, database performance, and system resources
"""

import subprocess
import json
import time
import requests
from datetime import datetime
import statistics
from typing import Dict, List, Any

class SystemMonitor:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.monitoring_data = []
        
    def get_docker_stats(self) -> Dict[str, Any]:
        """Get Docker container resource usage"""
        try:
            # Get container stats
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", 
                 "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                stats = {}
                
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        container_name = parts[0]
                        stats[container_name] = {
                            "cpu_percent": parts[1],
                            "memory_usage": parts[2],
                            "memory_percent": parts[3],
                            "network_io": parts[4],
                            "block_io": parts[5]
                        }
                
                return stats
            else:
                return {"error": "Failed to get Docker stats"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_api_health(self) -> Dict[str, Any]:
        """Check API health and response time"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "data": response.json()
                }
            else:
                return {
                    "status": "unhealthy", 
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_event_count(self) -> Dict[str, Any]:
        """Get current event count from API"""
        try:
            response = requests.get(f"{self.api_base_url}/events/count", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_export_status(self) -> Dict[str, Any]:
        """Get S3 export pipeline status"""
        try:
            response = requests.get(f"{self.api_base_url}/export/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_recent_events(self, limit: int = 5) -> Dict[str, Any]:
        """Get recent events to verify bulk processing"""
        try:
            response = requests.get(f"{self.api_base_url}/events/recent?limit={limit}", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_postgres_stats(self) -> Dict[str, Any]:
        """Get PostgreSQL performance stats via Docker exec"""
        try:
            # Get database connection stats
            conn_result = subprocess.run([
                "docker", "compose", "exec", "-T", "postgres", 
                "psql", "-U", "postgres", "-d", "postgres", "-t",
                "-c", "SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'postgres' GROUP BY state;"
            ], capture_output=True, text=True, timeout=10)
            
            # Get table stats
            table_result = subprocess.run([
                "docker", "compose", "exec", "-T", "postgres",
                "psql", "-U", "postgres", "-d", "postgres", "-t", 
                "-c", "SELECT n_tup_ins, n_tup_upd, n_live_tup FROM pg_stat_user_tables WHERE relname = 'events_log';"
            ], capture_output=True, text=True, timeout=10)
            
            stats = {}
            
            if conn_result.returncode == 0:
                connections = {}
                for line in conn_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.strip().split('|')
                        if len(parts) >= 2:
                            state = parts[0].strip()
                            count = parts[1].strip()
                            connections[state] = int(count) if count.isdigit() else count
                stats["connections"] = connections
            
            if table_result.returncode == 0:
                table_line = table_result.stdout.strip()
                if table_line:
                    parts = table_line.split('|')
                    if len(parts) >= 3:
                        stats["table_stats"] = {
                            "inserts": int(parts[0].strip()) if parts[0].strip().isdigit() else 0,
                            "updates": int(parts[1].strip()) if parts[1].strip().isdigit() else 0,
                            "live_rows": int(parts[2].strip()) if parts[2].strip().isdigit() else 0
                        }
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    def collect_monitoring_snapshot(self) -> Dict[str, Any]:
        """Collect a complete monitoring snapshot"""
        timestamp = datetime.now().isoformat()
        
        snapshot = {
            "timestamp": timestamp,
            "docker_stats": self.get_docker_stats(),
            "api_health": self.get_api_health(),
            "event_count": self.get_event_count(),
            "export_status": self.get_export_status(),
            "postgres_stats": self.get_postgres_stats(),
            "recent_events": self.get_recent_events()
        }
        
        return snapshot
    
    def start_monitoring(self, duration_seconds: int = 300, interval_seconds: int = 30):
        """Start continuous monitoring for specified duration"""
        print(f"🔍 Starting system monitoring for {duration_seconds} seconds")
        print(f"   Collecting data every {interval_seconds} seconds")
        print("   Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        snapshots_collected = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                snapshot = self.collect_monitoring_snapshot()
                self.monitoring_data.append(snapshot)
                snapshots_collected += 1
                
                # Print summary
                self.print_snapshot_summary(snapshot, snapshots_collected)
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        
        print(f"\n📊 Monitoring complete: {snapshots_collected} snapshots collected")
        return self.monitoring_data
    
    def print_snapshot_summary(self, snapshot: Dict[str, Any], snapshot_num: int):
        """Print a summary of the current snapshot"""
        timestamp = snapshot["timestamp"]
        print(f"[{timestamp}] Snapshot {snapshot_num}:")
        
        # API Health
        api_health = snapshot.get("api_health", {})
        if api_health.get("status") == "healthy":
            print(f"  ✅ API: {api_health.get('response_time_ms', 0):.1f}ms")
        else:
            print(f"  ❌ API: {api_health.get('status', 'unknown')}")
        
        # Event Count
        event_count = snapshot.get("event_count", {})
        if "total_events" in event_count:
            print(f"  📊 Events: {event_count['total_events']:,}")
        
        # Docker Stats
        docker_stats = snapshot.get("docker_stats", {})
        if not docker_stats.get("error"):
            for container, stats in docker_stats.items():
                if isinstance(stats, dict):
                    cpu = stats.get("cpu_percent", "0%").rstrip('%')
                    memory = stats.get("memory_usage", "0MB / 0MB")
                    print(f"  🐳 {container}: CPU {cpu}%, MEM {memory}")
        
        # PostgreSQL Stats
        pg_stats = snapshot.get("postgres_stats", {})
        if "connections" in pg_stats:
            active_conns = pg_stats["connections"].get("active", 0)
            idle_conns = pg_stats["connections"].get("idle", 0)
            print(f"  🗄️  PostgreSQL: {active_conns} active, {idle_conns} idle connections")
        
        if "table_stats" in pg_stats:
            inserts = pg_stats["table_stats"].get("inserts", 0)
            live_rows = pg_stats["table_stats"].get("live_rows", 0)
            print(f"  📈 DB Stats: {inserts:,} inserts, {live_rows:,} live rows")
        
        print()
    
    def analyze_monitoring_data(self) -> Dict[str, Any]:
        """Analyze collected monitoring data for insights"""
        if not self.monitoring_data:
            return {"error": "No monitoring data collected"}
        
        # Extract metrics over time
        api_response_times = []
        event_counts = []
        cpu_usage = {"fastapi": [], "postgres": []}
        
        for snapshot in self.monitoring_data:
            # API response times
            api_health = snapshot.get("api_health", {})
            if "response_time_ms" in api_health:
                api_response_times.append(api_health["response_time_ms"])
            
            # Event counts
            event_count = snapshot.get("event_count", {})
            if "total_events" in event_count:
                event_counts.append(event_count["total_events"])
            
            # CPU usage by container
            docker_stats = snapshot.get("docker_stats", {})
            for container, stats in docker_stats.items():
                if isinstance(stats, dict) and "cpu_percent" in stats:
                    cpu_str = stats["cpu_percent"].rstrip('%')
                    try:
                        cpu_val = float(cpu_str)
                        if "fastapi" in container.lower():
                            cpu_usage["fastapi"].append(cpu_val)
                        elif "postgres" in container.lower():
                            cpu_usage["postgres"].append(cpu_val)
                    except ValueError:
                        pass
        
        analysis = {
            "monitoring_duration_snapshots": len(self.monitoring_data),
            "api_performance": {},
            "event_processing": {},
            "resource_usage": {}
        }
        
        # API performance analysis
        if api_response_times:
            analysis["api_performance"] = {
                "avg_response_time_ms": statistics.mean(api_response_times),
                "max_response_time_ms": max(api_response_times),
                "min_response_time_ms": min(api_response_times),
                "response_time_stability": statistics.stdev(api_response_times) if len(api_response_times) > 1 else 0
            }
        
        # Event processing analysis
        if len(event_counts) >= 2:
            event_growth = event_counts[-1] - event_counts[0]
            time_span_minutes = len(event_counts) * 0.5  # Assuming 30-second intervals
            events_per_minute = event_growth / time_span_minutes if time_span_minutes > 0 else 0
            
            analysis["event_processing"] = {
                "total_events_processed": event_growth,
                "events_per_minute": events_per_minute,
                "events_per_second": events_per_minute / 60,
                "processing_rate_stability": statistics.stdev([event_counts[i] - event_counts[i-1] 
                                                              for i in range(1, len(event_counts))]) if len(event_counts) > 2 else 0
            }
        
        # Resource usage analysis
        for service, cpu_values in cpu_usage.items():
            if cpu_values:
                analysis["resource_usage"][f"{service}_cpu"] = {
                    "avg_cpu_percent": statistics.mean(cpu_values),
                    "max_cpu_percent": max(cpu_values),
                    "cpu_stability": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
                }
        
        return analysis

def main():
    monitor = SystemMonitor()
    
    print("🔬 Evothesis System Monitoring Tool")
    print("=" * 40)
    
    # Quick system check
    print("📋 Pre-monitoring system check...")
    snapshot = monitor.collect_monitoring_snapshot()
    monitor.print_snapshot_summary(snapshot, 0)
    
    # Ask user for monitoring duration
    try:
        duration = int(input("Enter monitoring duration in seconds (default 300): ") or "300")
        interval = int(input("Enter monitoring interval in seconds (default 30): ") or "30")
    except ValueError:
        duration = 300
        interval = 30
    
    # Start monitoring
    monitoring_data = monitor.start_monitoring(duration, interval)
    
    # Analyze results
    if monitoring_data:
        print("\n📊 Analyzing monitoring data...")
        analysis = monitor.analyze_monitoring_data()
        
        if "error" not in analysis:
            print("\n🎯 System Performance Analysis:")
            print("=" * 40)
            
            # API Performance
            api_perf = analysis.get("api_performance", {})
            if api_perf:
                print(f"API Performance:")
                print(f"  Average Response Time: {api_perf.get('avg_response_time_ms', 0):.1f}ms")
                print(f"  Max Response Time: {api_perf.get('max_response_time_ms', 0):.1f}ms")
                print(f"  Response Stability: {api_perf.get('response_time_stability', 0):.1f}ms stddev")
            
            # Event Processing
            event_proc = analysis.get("event_processing", {})
            if event_proc:
                print(f"\nEvent Processing:")
                print(f"  Events Processed: {event_proc.get('total_events_processed', 0):,}")
                print(f"  Events per Second: {event_proc.get('events_per_second', 0):.2f}")
                print(f"  Processing Rate Stability: {event_proc.get('processing_rate_stability', 0):.1f}")
            
            # Resource Usage
            resource_usage = analysis.get("resource_usage", {})
            if resource_usage:
                print(f"\nResource Usage:")
                for service, metrics in resource_usage.items():
                    service_name = service.replace("_cpu", "").title()
                    print(f"  {service_name} CPU: {metrics.get('avg_cpu_percent', 0):.1f}% avg, "
                          f"{metrics.get('max_cpu_percent', 0):.1f}% max")
        
        # Export raw data for analysis
        import json
        with open(f"monitoring_data_{int(time.time())}.json", "w") as f:
            json.dump({
                "monitoring_data": monitoring_data,
                "analysis": analysis
            }, f, indent=2)
        
        print(f"\n💾 Raw monitoring data exported to monitoring_data_{int(time.time())}.json")

if __name__ == "__main__":
    main()
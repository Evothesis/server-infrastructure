#!/usr/bin/env python3
"""
Extreme Stress Testing for Evothesis - Find the Breaking Point
Progressive load testing to discover maximum capacity
"""

import asyncio
import aiohttp
import json
import time
import random
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any
import psutil
import sys

class ExtremeStressTester:
    def __init__(self):
        self.api_url = "http://localhost:8000/collect"
        self.results = []
        self.total_events_sent = 0
        self.total_requests_sent = 0
        self.start_time = None
        self.failure_threshold = 5  # Stop if >5% failure rate
        
    def generate_batch_event(self, batch_size: int) -> Dict[str, Any]:
        """Generate realistic batch event - optimized for speed"""
        session_id = f"extreme_{random.randint(100000, 999999)}"
        visitor_id = f"extreme_{random.randint(100000, 999999)}"
        site_id = random.choice(["extreme-test-1", "extreme-test-2", "extreme-test-3"])
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Generate events efficiently
        events = []
        event_types = ["click", "scroll", "pageview", "form", "copy"]
        
        for i in range(batch_size - 1):
            events.append({
                "eventType": event_types[i % len(event_types)],
                "timestamp": timestamp,
                "eventData": {"index": i, "batch_test": True}
            })
        
        return {
            "eventType": "batch",
            "sessionId": session_id,
            "visitorId": visitor_id,
            "siteId": site_id,
            "timestamp": timestamp,
            "url": f"https://{site_id}/extreme-test",
            "path": "/extreme-test",
            "events": events,
            "batchMetadata": {
                "eventCount": len(events) + 1,
                "testType": "extreme"
            }
        }
    
    async def send_batch_optimized(self, session: aiohttp.ClientSession, batch_size: int) -> tuple[bool, float, int]:
        """Optimized batch sending with minimal overhead"""
        batch_event = self.generate_batch_event(batch_size)
        
        start_time = time.perf_counter()
        try:
            async with session.post(
                self.api_url,
                json=batch_event,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.perf_counter() - start_time
                success = response.status == 200
                
                if success:
                    self.total_events_sent += batch_size
                    self.total_requests_sent += 1
                
                return success, response_time, batch_size
                
        except Exception as e:
            response_time = time.perf_counter() - start_time
            return False, response_time, batch_size
    
    def get_system_stats(self):
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        }
    
    async def progressive_load_test(self, start_eps: int, max_eps: int, step_eps: int, duration_per_step: int):
        """Progressive load testing to find breaking point"""
        print(f"🔥 EXTREME STRESS TESTING - FINDING THE LIMIT")
        print(f"   Starting at: {start_eps} EPS")
        print(f"   Maximum target: {max_eps} EPS") 
        print(f"   Step size: {step_eps} EPS")
        print(f"   Duration per step: {duration_per_step} seconds")
        print(f"   Failure threshold: {self.failure_threshold}%")
        print("=" * 60)
        
        connector = aiohttp.TCPConnector(
            limit=500,  # Increased connection pool
            limit_per_host=200,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=10, connect=2)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            
            for target_eps in range(start_eps, max_eps + 1, step_eps):
                print(f"\n🚀 Testing {target_eps} events/second...")
                
                # System stats before test
                pre_stats = self.get_system_stats()
                
                # Reset counters
                step_start_time = time.time()
                step_events = 0
                step_requests = 0
                step_failures = 0
                response_times = []
                batch_sizes = []
                
                # Calculate batch timing for this step
                target_batches_per_second = target_eps / 12  # Assume 12 events per batch average
                batch_interval = 1.0 / target_batches_per_second
                concurrent_workers = min(100, int(target_batches_per_second * 2))  # 2x batches as workers
                
                print(f"   Workers: {concurrent_workers}")
                print(f"   Target batches/sec: {target_batches_per_second:.2f}")
                
                # Run load test for this step
                tasks = []
                
                async def worker(worker_id: int):
                    nonlocal step_events, step_requests, step_failures, response_times, batch_sizes
                    
                    worker_start = time.time()
                    while time.time() - worker_start < duration_per_step:
                        batch_size = random.randint(10, 18)  # Larger batches for extreme test
                        
                        success, response_time, actual_batch_size = await self.send_batch_optimized(session, batch_size)
                        
                        if success:
                            step_events += actual_batch_size
                            step_requests += 1
                            response_times.append(response_time)
                            batch_sizes.append(actual_batch_size)
                        else:
                            step_failures += 1
                        
                        # Brief pause to control rate
                        await asyncio.sleep(batch_interval / concurrent_workers)
                
                # Start workers
                for i in range(concurrent_workers):
                    task = asyncio.create_task(worker(i))
                    tasks.append(task)
                
                # Wait for completion
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Calculate step results
                step_duration = time.time() - step_start_time
                actual_eps = step_events / step_duration
                success_rate = (step_requests / (step_requests + step_failures)) * 100 if (step_requests + step_failures) > 0 else 0
                
                # System stats after test
                post_stats = self.get_system_stats()
                
                # Step results
                step_results = {
                    "target_eps": target_eps,
                    "actual_eps": actual_eps,
                    "success_rate": success_rate,
                    "total_events": step_events,
                    "total_requests": step_requests,
                    "failures": step_failures,
                    "avg_response_ms": statistics.mean(response_times) * 1000 if response_times else 0,
                    "p95_response_ms": statistics.quantiles(response_times, n=20)[18] * 1000 if len(response_times) >= 20 else (max(response_times) * 1000 if response_times else 0),
                    "avg_batch_size": statistics.mean(batch_sizes) if batch_sizes else 0,
                    "cpu_usage": post_stats["cpu_percent"],
                    "memory_usage": post_stats["memory_percent"]
                }
                
                self.results.append(step_results)
                
                # Print step results
                print(f"   📊 Results:")
                print(f"      Actual EPS: {actual_eps:.2f}")
                print(f"      Success Rate: {success_rate:.1f}%")
                print(f"      Events Processed: {step_events:,}")
                print(f"      Avg Response: {step_results['avg_response_ms']:.1f}ms")
                print(f"      P95 Response: {step_results['p95_response_ms']:.1f}ms")
                print(f"      CPU Usage: {post_stats['cpu_percent']:.1f}%")
                print(f"      Memory Usage: {post_stats['memory_percent']:.1f}%")
                print(f"      Avg Batch Size: {step_results['avg_batch_size']:.1f}")
                
                # Check if we hit failure threshold
                if success_rate < (100 - self.failure_threshold):
                    print(f"\n🛑 FAILURE THRESHOLD REACHED!")
                    print(f"   Success rate {success_rate:.1f}% below {100 - self.failure_threshold}%")
                    print(f"   Maximum capacity found: ~{target_eps - step_eps} EPS")
                    break
                
                # Check if system resources are maxed
                if post_stats["cpu_percent"] > 90 or post_stats["memory_percent"] > 90:
                    print(f"\n⚠️  SYSTEM RESOURCE LIMIT REACHED!")
                    print(f"   CPU: {post_stats['cpu_percent']:.1f}% | Memory: {post_stats['memory_percent']:.1f}%")
                    if target_eps < max_eps:
                        print(f"   Continuing to test higher loads...")
                
                # Brief cooldown between steps
                if target_eps < max_eps:
                    print(f"   ⏳ Cooling down for 5 seconds...")
                    await asyncio.sleep(5)
        
        return self.results
    
    def analyze_extreme_results(self) -> Dict[str, Any]:
        """Analyze extreme test results to find limits"""
        if not self.results:
            return {"error": "No test results"}
        
        # Find peak performance
        successful_tests = [r for r in self.results if r["success_rate"] >= 95]
        all_tests = self.results
        
        if successful_tests:
            peak_eps = max(successful_tests, key=lambda x: x["actual_eps"])
            max_throughput = max(r["actual_eps"] for r in successful_tests)
        else:
            peak_eps = max(all_tests, key=lambda x: x["actual_eps"]) if all_tests else {}
            max_throughput = max(r["actual_eps"] for r in all_tests) if all_tests else 0
        
        # Resource analysis
        max_cpu = max(r["cpu_usage"] for r in all_tests) if all_tests else 0
        max_memory = max(r["memory_usage"] for r in all_tests) if all_tests else 0
        
        # Performance degradation analysis
        degradation_point = None
        for i, result in enumerate(all_tests):
            if result["success_rate"] < 98 or result["p95_response_ms"] > 200:
                degradation_point = result["target_eps"]
                break
        
        return {
            "max_reliable_eps": max_throughput,
            "peak_performance": peak_eps,
            "degradation_starts_at": degradation_point,
            "max_cpu_usage": max_cpu,
            "max_memory_usage": max_memory,
            "total_events_tested": sum(r["total_events"] for r in all_tests),
            "test_steps_completed": len(all_tests)
        }

async def main():
    tester = ExtremeStressTester()
    
    print("🔥 EVOTHESIS EXTREME LIMITS TESTING")
    print("Finding the absolute breaking point of bulk insert optimization")
    print("=" * 70)
    
    # Get user input for test parameters
    try:
        start_eps = int(input("Starting events/second (default 20): ") or "20")
        max_eps = int(input("Maximum events/second to test (default 100): ") or "100") 
        step_eps = int(input("Step size (default 10): ") or "10")
        duration = int(input("Duration per step in seconds (default 30): ") or "30")
    except ValueError:
        start_eps, max_eps, step_eps, duration = 20, 100, 10, 30
    
    print(f"\n🎯 Test Configuration:")
    print(f"   Range: {start_eps} → {max_eps} EPS")
    print(f"   Step: {step_eps} EPS")
    print(f"   Duration: {duration}s per step")
    print(f"   Estimated total time: {((max_eps - start_eps) // step_eps + 1) * duration // 60} minutes")
    
    confirm = input("\nProceed with extreme testing? (y/N): ")
    if confirm.lower() != 'y':
        print("Test cancelled.")
        return
    
    # Pre-test system check
    print(f"\n📋 Pre-test system status:")
    pre_stats = tester.get_system_stats()
    print(f"   CPU: {pre_stats['cpu_percent']:.1f}%")
    print(f"   Memory: {pre_stats['memory_percent']:.1f}%")
    print(f"   Available Memory: {pre_stats['memory_available_gb']:.1f}GB")
    
    # Run extreme stress test
    results = await tester.progressive_load_test(start_eps, max_eps, step_eps, duration)
    
    # Analyze results
    analysis = tester.analyze_extreme_results()
    
    print(f"\n🏆 EXTREME TESTING RESULTS")
    print("=" * 50)
    print(f"Maximum Reliable Throughput: {analysis['max_reliable_eps']:.2f} EPS")
    print(f"Total Events Processed: {analysis['total_events_tested']:,}")
    print(f"Test Steps Completed: {analysis['test_steps_completed']}")
    print(f"Peak CPU Usage: {analysis['max_cpu_usage']:.1f}%")
    print(f"Peak Memory Usage: {analysis['max_memory_usage']:.1f}%")
    
    if analysis['degradation_starts_at']:
        print(f"Performance Degradation At: {analysis['degradation_starts_at']} EPS")
    
    # Business impact analysis
    max_eps = analysis['max_reliable_eps']
    monthly_events = max_eps * 60 * 60 * 24 * 30  # Events per month
    monthly_revenue = (monthly_events / 1000) * 0.01  # Revenue at $0.01/1000 events
    
    print(f"\n💰 BUSINESS IMPACT ANALYSIS")
    print("=" * 40)
    print(f"MacBook Pro Capacity: {max_eps:.0f} events/second")
    print(f"Monthly Event Capacity: {monthly_events/1_000_000:.0f}M events")
    print(f"Revenue Potential: ${monthly_revenue:,.0f}/month")
    print(f"Agency Clients Supported: {int(max_eps / 6)} (at 6 EPS each)")
    
    print(f"\n🚀 PRODUCTION SERVER PROJECTION")
    print("=" * 40)
    server_multiplier = 3  # Conservative estimate for production server
    print(f"Production Capacity: {max_eps * server_multiplier:.0f} events/second")
    print(f"Production Monthly: {(monthly_events * server_multiplier)/1_000_000:.0f}M events")
    print(f"Production Revenue: ${monthly_revenue * server_multiplier:,.0f}/month")
    
    # Next steps
    print(f"\n📋 VALIDATION COMMANDS")
    print("=" * 30)
    print(f"curl http://localhost:8000/events/count")
    print(f"docker compose logs fastapi | grep 'Bulk inserted' | wc -l")
    print(f"docker stats --no-stream")

if __name__ == "__main__":
    # Install required package if not available
    try:
        import psutil
    except ImportError:
        print("Installing psutil for system monitoring...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    asyncio.run(main())
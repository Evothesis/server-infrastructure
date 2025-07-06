#!/usr/bin/env python3
"""
Direct Database Stress Test - Bypass AsyncIO Completely
Test the TRUE limits of bulk insert optimization
"""

import threading
import time
import random
import statistics
import queue
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import concurrent.futures
import psutil
import requests
import sys

class DirectDatabaseStressTester:
    def __init__(self):
        self.api_url = "http://localhost:8000/collect"
        self.results_queue = queue.Queue()
        self.total_events = 0
        self.total_requests = 0
        self.start_time = None
        
    def generate_batch_event(self, batch_size: int, thread_id: int) -> Dict[str, Any]:
        """Generate batch event optimized for speed"""
        session_id = f"direct_{thread_id}_{random.randint(1000, 9999)}"
        visitor_id = f"direct_{thread_id}_{random.randint(1000, 9999)}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Pre-generated event types for speed
        event_types = ["click", "scroll", "pageview", "form", "copy"]
        
        events = []
        for i in range(batch_size - 1):
            events.append({
                "eventType": event_types[i % len(event_types)],
                "timestamp": timestamp,
                "eventData": {"thread": thread_id, "index": i}
            })
        
        return {
            "eventType": "batch",
            "sessionId": session_id,
            "visitorId": visitor_id,
            "siteId": f"direct-test-{thread_id % 5}",
            "timestamp": timestamp,
            "url": f"https://direct-test-{thread_id % 5}/stress",
            "path": "/stress",
            "events": events,
            "batchMetadata": {
                "eventCount": len(events) + 1,
                "threadId": thread_id
            }
        }
    
    def worker_thread(self, thread_id: int, events_per_second: float, duration: int, batch_size_range: tuple):
        """Single worker thread hitting database directly"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Calculate timing
        batches_per_second = events_per_second / ((batch_size_range[0] + batch_size_range[1]) / 2)
        batch_interval = 1.0 / batches_per_second
        
        thread_start = time.perf_counter()
        thread_events = 0
        thread_requests = 0
        thread_failures = 0
        response_times = []
        
        while time.perf_counter() - thread_start < duration:
            batch_size = random.randint(*batch_size_range)
            batch_event = self.generate_batch_event(batch_size, thread_id)
            
            request_start = time.perf_counter()
            try:
                response = session.post(self.api_url, json=batch_event, timeout=5)
                response_time = time.perf_counter() - request_start
                
                if response.status_code == 200:
                    thread_events += batch_size
                    thread_requests += 1
                    response_times.append(response_time)
                else:
                    thread_failures += 1
                    
            except Exception as e:
                thread_failures += 1
                response_time = time.perf_counter() - request_start
            
            # Precise timing control
            time.sleep(max(0, batch_interval - response_time))
        
        # Store results
        self.results_queue.put({
            "thread_id": thread_id,
            "events": thread_events,
            "requests": thread_requests,
            "failures": thread_failures,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0
        })
        
        session.close()
    
    def run_direct_stress_test(self, target_eps: int, num_threads: int, duration: int, batch_size_range: tuple = (12, 18)):
        """Run direct multi-threaded stress test"""
        print(f"\n🔥 DIRECT DATABASE STRESS TEST")
        print(f"   Target: {target_eps} events/second")
        print(f"   Threads: {num_threads}")
        print(f"   Duration: {duration} seconds")
        print(f"   Batch Size: {batch_size_range[0]}-{batch_size_range[1]} events")
        print(f"   Events per thread: {target_eps / num_threads:.1f}/second")
        
        # Clear results queue
        while not self.results_queue.empty():
            self.results_queue.get()
        
        # Get system stats before
        pre_stats = self.get_system_stats()
        print(f"   Pre-test CPU: {pre_stats['cpu_percent']:.1f}%")
        print(f"   Pre-test Memory: {pre_stats['memory_percent']:.1f}%")
        
        # Start threads
        self.start_time = time.perf_counter()
        threads = []
        
        events_per_thread = target_eps / num_threads
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=self.worker_thread,
                args=(i, events_per_thread, duration, batch_size_range)
            )
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        test_duration = time.perf_counter() - self.start_time
        
        # Collect results
        thread_results = []
        total_events = 0
        total_requests = 0
        total_failures = 0
        all_response_times = []
        
        while not self.results_queue.empty():
            result = self.results_queue.get()
            thread_results.append(result)
            total_events += result["events"]
            total_requests += result["requests"]
            total_failures += result["failures"]
            if result["avg_response_time"] > 0:
                all_response_times.append(result["avg_response_time"])
        
        # Get system stats after
        post_stats = self.get_system_stats()
        
        # Calculate final metrics
        actual_eps = total_events / test_duration
        success_rate = (total_requests / (total_requests + total_failures)) * 100 if (total_requests + total_failures) > 0 else 0
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        
        return {
            "target_eps": target_eps,
            "actual_eps": actual_eps,
            "total_events": total_events,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "success_rate": success_rate,
            "test_duration": test_duration,
            "avg_response_time_ms": avg_response_time * 1000,
            "pre_cpu": pre_stats["cpu_percent"],
            "post_cpu": post_stats["cpu_percent"],
            "pre_memory": pre_stats["memory_percent"], 
            "post_memory": post_stats["memory_percent"],
            "threads_used": num_threads
        }
    
    def get_system_stats(self):
        """Get system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3)
        }
    
    def run_escalating_test(self):
        """Run escalating test to find true database limits"""
        print("🚀 FINDING TRUE DATABASE LIMITS")
        print("Testing with direct threading (no AsyncIO bottleneck)")
        print("=" * 60)
        
        # Test configuration
        test_configs = [
            (100, 10, 30),   # 100 EPS, 10 threads, 30 seconds
            (200, 20, 30),   # 200 EPS, 20 threads, 30 seconds  
            (400, 30, 30),   # 400 EPS, 30 threads, 30 seconds
            (600, 40, 30),   # 600 EPS, 40 threads, 30 seconds
            (800, 50, 30),   # 800 EPS, 50 threads, 30 seconds
            (1000, 60, 30),  # 1000 EPS, 60 threads, 30 seconds
            (1500, 80, 30),  # 1500 EPS, 80 threads, 30 seconds
            (2000, 100, 30), # 2000 EPS, 100 threads, 30 seconds
        ]
        
        results = []
        
        for target_eps, num_threads, duration in test_configs:
            print(f"\n🔥 Testing {target_eps} EPS with {num_threads} threads...")
            
            result = self.run_direct_stress_test(target_eps, num_threads, duration)
            results.append(result)
            
            print(f"   📊 Results:")
            print(f"      Actual EPS: {result['actual_eps']:.2f}")
            print(f"      Success Rate: {result['success_rate']:.1f}%")
            print(f"      Events: {result['total_events']:,}")
            print(f"      Avg Response: {result['avg_response_time_ms']:.1f}ms")
            print(f"      CPU: {result['pre_cpu']:.1f}% → {result['post_cpu']:.1f}%")
            print(f"      Memory: {result['pre_memory']:.1f}% → {result['post_memory']:.1f}%")
            
            # Stop if we hit significant failures or extreme response times
            if result['success_rate'] < 95 or result['avg_response_time_ms'] > 1000:
                print(f"\n🛑 LIMIT REACHED!")
                print(f"   Success rate: {result['success_rate']:.1f}%")
                print(f"   Response time: {result['avg_response_time_ms']:.1f}ms")
                break
            
            # Brief cooldown
            print("   ⏳ Cooling down for 5 seconds...")
            time.sleep(5)
        
        return results

def main():
    try:
        import psutil
    except ImportError:
        print("Installing psutil...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    tester = DirectDatabaseStressTester()
    
    print("🔥 DIRECT DATABASE STRESS TESTING")
    print("Bypassing AsyncIO to find TRUE database limits")
    print("=" * 50)
    
    # Get baseline
    print("📋 Getting baseline event count...")
    try:
        response = requests.get("http://localhost:8000/events/count", timeout=5)
        if response.status_code == 200:
            baseline_events = response.json()["total_events"]
            print(f"   Baseline events: {baseline_events:,}")
        else:
            baseline_events = 0
            print("   Could not get baseline")
    except:
        baseline_events = 0
        print("   Could not get baseline")
    
    # Choice of test type
    print("\nTest Options:")
    print("1. Single high-intensity test (1000 EPS)")
    print("2. Progressive escalation test (100 → 2000 EPS)")
    print("3. Custom test")
    
    choice = input("Select test type (1/2/3): ").strip()
    
    if choice == "1":
        # Single high test
        result = tester.run_direct_stress_test(1000, 60, 60)
        print(f"\n🏆 SINGLE TEST RESULTS:")
        print(f"   Target: {result['target_eps']} EPS")
        print(f"   Achieved: {result['actual_eps']:.2f} EPS")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Total Events: {result['total_events']:,}")
        
    elif choice == "2":
        # Progressive test
        results = tester.run_escalating_test()
        
        # Find best performance
        successful_results = [r for r in results if r['success_rate'] >= 98]
        if successful_results:
            best_result = max(successful_results, key=lambda x: x['actual_eps'])
            print(f"\n🏆 MAXIMUM RELIABLE PERFORMANCE:")
            print(f"   Peak EPS: {best_result['actual_eps']:.2f}")
            print(f"   Success Rate: {best_result['success_rate']:.1f}%")
            print(f"   Response Time: {best_result['avg_response_time_ms']:.1f}ms")
        
    else:
        # Custom test
        try:
            target_eps = int(input("Target events/second: "))
            num_threads = int(input("Number of threads: "))
            duration = int(input("Duration (seconds): "))
            
            result = tester.run_direct_stress_test(target_eps, num_threads, duration)
            print(f"\n🏆 CUSTOM TEST RESULTS:")
            print(f"   Achieved: {result['actual_eps']:.2f} EPS")
            print(f"   Success Rate: {result['success_rate']:.1f}%")
            
        except ValueError:
            print("Invalid input. Exiting.")
            return
    
    # Final verification
    print(f"\n📋 VERIFICATION COMMANDS:")
    print(f"curl http://localhost:8000/events/count")
    print(f"docker compose logs fastapi | grep 'Bulk inserted' | wc -l")
    
    try:
        response = requests.get("http://localhost:8000/events/count", timeout=5)
        if response.status_code == 200:
            final_events = response.json()["total_events"]
            new_events = final_events - baseline_events
            print(f"\n📊 FINAL COUNT:")
            print(f"   Events processed: {new_events:,}")
            print(f"   Total in database: {final_events:,}")
    except:
        print("Could not get final count")

if __name__ == "__main__":
    main()
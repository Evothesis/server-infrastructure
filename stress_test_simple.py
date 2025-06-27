#!/usr/bin/env python3
"""
Simplified Evothesis Stress Test for Zero-Baseline Environment
Optimized for clean measurement of bulk insert performance
"""

import asyncio
import aiohttp
import json
import time
import random
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any
import sys

class SimpleStressTester:
    def __init__(self):
        self.api_url = "http://localhost:8000/collect"
        self.results = []
        self.total_events_sent = 0
        self.total_requests_sent = 0
        self.start_time = None
        
    def generate_batch_event(self, batch_size: int) -> Dict[str, Any]:
        """Generate realistic batch event"""
        session_id = f"stress_sess_{random.randint(100000, 999999)}"
        visitor_id = f"stress_vis_{random.randint(100000, 999999)}"
        site_id = random.choice(["agency-client-1-com", "agency-client-2-com", "localhost"])
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Generate individual events for the batch
        events = []
        event_types = ["click", "scroll", "pageview", "form_focus", "text_copy"]
        
        for _ in range(batch_size - 1):  # -1 because batch event itself counts
            events.append({
                "eventType": random.choice(event_types),
                "timestamp": timestamp,
                "eventData": {
                    "test": True,
                    "value": random.randint(1, 100)
                }
            })
        
        return {
            "eventType": "batch",
            "sessionId": session_id,
            "visitorId": visitor_id,
            "siteId": site_id,
            "timestamp": timestamp,
            "url": f"https://{site_id.replace('-', '.')}/stress-test",
            "path": "/stress-test",
            "events": events,
            "batchMetadata": {
                "eventCount": len(events) + 1,
                "sentOnExit": False
            }
        }
    
    async def send_batch(self, session: aiohttp.ClientSession, batch_size: int) -> tuple[bool, float, int]:
        """Send a batch event and measure performance"""
        batch_event = self.generate_batch_event(batch_size)
        
        start_time = time.time()
        try:
            async with session.post(
                self.api_url,
                json=batch_event,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                success = response.status == 200
                
                if success:
                    self.total_events_sent += batch_size
                    self.total_requests_sent += 1
                
                return success, response_time, batch_size
                
        except Exception as e:
            response_time = time.time() - start_time
            print(f"Request failed: {e}")
            return False, response_time, batch_size
    
    async def run_load_test(self, target_events_per_second: float, duration_seconds: int):
        """Run load test with specified parameters"""
        print(f"\n🚀 Running Load Test:")
        print(f"   Target: {target_events_per_second} events/second")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Expected total events: {target_events_per_second * duration_seconds:.0f}")
        
        self.start_time = time.time()
        self.results = []
        self.total_events_sent = 0
        self.total_requests_sent = 0
        
        # Calculate timing
        target_batches_per_second = target_events_per_second / 10  # Assume avg 10 events per batch
        batch_interval = 1.0 / target_batches_per_second
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Schedule batch sends
            for i in range(int(duration_seconds * target_batches_per_second)):
                # Random batch size between 8-15 (optimal range)
                batch_size = random.randint(8, 15)
                
                # Create task with delay
                delay = i * batch_interval
                task = asyncio.create_task(self._delayed_batch_send(session, delay, batch_size))
                tasks.append(task)
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            success_count = 0
            response_times = []
            batch_sizes = []
            
            for result in results:
                if isinstance(result, tuple) and len(result) == 3:
                    success, response_time, batch_size = result
                    if success:
                        success_count += 1
                        response_times.append(response_time)
                        batch_sizes.append(batch_size)
        
        # Calculate final statistics
        elapsed_time = time.time() - self.start_time
        success_rate = (success_count / len(tasks)) * 100 if tasks else 0
        
        stats = {
            "duration_seconds": elapsed_time,
            "total_requests": len(tasks),
            "successful_requests": success_count,
            "total_events_sent": self.total_events_sent,
            "success_rate": success_rate,
            "events_per_second": self.total_events_sent / elapsed_time,
            "requests_per_second": success_count / elapsed_time,
            "avg_response_time_ms": statistics.mean(response_times) * 1000 if response_times else 0,
            "max_response_time_ms": max(response_times) * 1000 if response_times else 0,
            "avg_batch_size": statistics.mean(batch_sizes) if batch_sizes else 0,
        }
        
        return stats
    
    async def _delayed_batch_send(self, session: aiohttp.ClientSession, delay: float, batch_size: int):
        """Send a batch after specified delay"""
        await asyncio.sleep(delay)
        return await self.send_batch(session, batch_size)
    
    def print_results(self, stats: Dict[str, Any], test_name: str):
        """Print formatted test results"""
        print(f"\n📈 {test_name} Results:")
        print(f"   Duration: {stats['duration_seconds']:.1f}s")
        print(f"   Total Events: {stats['total_events_sent']:,}")
        print(f"   Events/Second: {stats['events_per_second']:.2f}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Avg Response: {stats['avg_response_time_ms']:.1f}ms")
        print(f"   Max Response: {stats['max_response_time_ms']:.1f}ms")
        print(f"   Avg Batch Size: {stats['avg_batch_size']:.1f}")
        print(f"   Requests/Second: {stats['requests_per_second']:.2f}")

async def main():
    tester = SimpleStressTester()
    
    print("🔬 Evothesis Bulk Insert Performance Test")
    print("=" * 45)
    
    # Test 1: Light Load (2 events/second for 60 seconds)
    print("\n🔄 Phase 1: Light Load Test (Bulk Processing Verification)")
    light_stats = await tester.run_load_test(2.0, 60)
    tester.print_results(light_stats, "Light Load (2 EPS)")
    
    if light_stats['success_rate'] < 95:
        print("❌ Light load test failed. Stopping.")
        return
    
    print("\n⏳ Cooling down for 10 seconds...")
    await asyncio.sleep(10)
    
    # Test 2: Agency Client Load (6 events/second for 300 seconds)
    print("\n🎯 Phase 2: Agency Client Simulation (6 EPS × 5 minutes)")
    agency_stats = await tester.run_load_test(6.0, 300)
    tester.print_results(agency_stats, "Agency Client Load (6 EPS)")
    
    print("\n⏳ Cooling down for 10 seconds...")
    await asyncio.sleep(10)
    
    # Test 3: Burst Capacity (15 events/second for 60 seconds)
    print("\n💥 Phase 3: Burst Capacity Test (Peak Traffic)")
    burst_stats = await tester.run_load_test(15.0, 60)
    tester.print_results(burst_stats, "Burst Capacity (15 EPS)")
    
    # Final Assessment
    print(f"\n🏆 Performance Assessment:")
    print("=" * 30)
    
    # Agency client readiness
    agency_ready = (
        agency_stats['success_rate'] >= 99.0 and
        agency_stats['events_per_second'] >= 5.5 and  # 95% of target
        agency_stats['avg_response_time_ms'] <= 100
    )
    
    if agency_ready:
        print("✅ PASSED: Platform ready for agency client deployment")
        print(f"   ✓ Success rate: {agency_stats['success_rate']:.1f}% (target: >99%)")
        print(f"   ✓ Throughput: {agency_stats['events_per_second']:.1f} EPS (target: >5.5)")
        print(f"   ✓ Response time: {agency_stats['avg_response_time_ms']:.1f}ms (target: <100ms)")
    else:
        print("⚠️  REVIEW NEEDED: Performance issues detected")
        if agency_stats['success_rate'] < 99.0:
            print(f"   ⚠️  Success rate: {agency_stats['success_rate']:.1f}% (target: >99%)")
        if agency_stats['events_per_second'] < 5.5:
            print(f"   ⚠️  Throughput: {agency_stats['events_per_second']:.1f} EPS (target: >5.5)")
        if agency_stats['avg_response_time_ms'] > 100:
            print(f"   ⚠️  Response time: {agency_stats['avg_response_time_ms']:.1f}ms (target: <100ms)")
    
    print(f"\n📊 Summary Statistics:")
    print(f"   Phase 1 (Light): {light_stats['total_events_sent']:,} events, {light_stats['success_rate']:.1f}% success")
    print(f"   Phase 2 (Agency): {agency_stats['total_events_sent']:,} events, {agency_stats['success_rate']:.1f}% success")  
    print(f"   Phase 3 (Burst): {burst_stats['total_events_sent']:,} events, {burst_stats['success_rate']:.1f}% success")
    
    total_events = light_stats['total_events_sent'] + agency_stats['total_events_sent'] + burst_stats['total_events_sent']
    print(f"   Total Test Events: {total_events:,}")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Check final event count: curl http://localhost:8000/events/count")
    print(f"   2. Verify bulk processing: docker compose logs fastapi | grep 'Bulk inserted' | wc -l")
    print(f"   3. Check container stats: docker stats --no-stream")
    print(f"   4. Review database performance: docker compose logs postgres | tail -20")

if __name__ == "__main__":
    asyncio.run(main())
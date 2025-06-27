STRESS TESTING PROMPT FOR EVOTHESIS ANALYTICS PLATFORM
I'm working on Evothesis, a data-as-a-service analytics platform with bulk insert optimization. I've just completed implementing enterprise-grade bulk insert processing that provides 50-100x performance improvement over individual database transactions.
CURRENT STATUS:
✅ Bulk insert optimization implemented and verified with test batches
✅ Environment-based scaling (development/production configurations)
✅ PostgreSQL write-optimized with connection pooling
✅ S3 export pipeline complete with client bucket integration
✅ All documentation updated with performance benchmarks
IMMEDIATE GOAL:
Stress test the platform to validate it can handle an agency client with:

500k pageviews/day (15M monthly across all client sites)
Estimated 200-300M events/month with comprehensive behavioral tracking
Target revenue: $2,000-3,000/month at $0.01 per 1,000 events

TECHNICAL ARCHITECTURE:

FastAPI backend with bulk insert optimization (db.bulk_insert_mappings())
PostgreSQL with write-optimized configuration and environment scaling
Tracking pixel with activity-based batching (60-second timeout)
Docker Compose deployment with .env.development configuration

VERIFIED PERFORMANCE:

Single events: 1 transaction per event
Batch events: 1 transaction per batch (tested with 4 events in single transaction)
Database verification: Identical created_at timestamps prove bulk operation
Logs confirm: "Processing batch with X individual events" and "Bulk inserted X events"

STRESS TESTING OBJECTIVES:

Volume Testing: Simulate 500k events/day load to verify bulk processing scales
Database Performance: Monitor connection pool, memory usage, write throughput
Batch Processing: Verify bulk insert optimization maintains performance under load
Infrastructure Limits: Identify bottlenecks and resource requirements
S3 Export: Test export pipeline performance under high event volume

CURRENT ENVIRONMENT:

Running on 2015 MacBook Pro with optimized PostgreSQL settings
Development environment with 512MB PostgreSQL memory limit
All services healthy: curl http://localhost:8000/health returns "connected"
Recent events verified: curl http://localhost:8000/events/recent shows proper storage

KEY FILES TO REFERENCE:

api/app/main.py - Bulk insert implementation with batch processing
api/app/database.py - Write-optimized connection pool configuration
docker-compose.yml - Environment-based scaling configuration
.env.development - Current development settings

PERFORMANCE VERIFICATION COMMANDS:
bash# Check bulk insert logs
docker compose logs fastapi | grep "Bulk inserted"

# Monitor database performance  
docker compose logs postgres | grep -i performance

# Test batch processing
curl -X POST http://localhost:8000/collect -H "Content-Type: application/json" \
  -d '{"eventType":"batch","sessionId":"stress_test","siteId":"localhost","events":[{"eventType":"click"},{"eventType":"scroll"}]}'
STRESS TESTING APPROACH NEEDED:

Synthetic event generation at target volume (500k/day = ~6 events/second)
Database monitoring during sustained load
Memory/CPU utilization tracking
Bulk insert efficiency measurement
Identification of performance bottlenecks and scaling requirements

SUCCESS CRITERIA:

Handle 6+ events/second sustained load without performance degradation
Maintain bulk insert processing efficiency (avg 8-15 events per batch)
Database connection pool remains healthy under load
Memory usage stays within configured limits
Clear identification of scaling requirements for production deployment

Please help me design and execute a comprehensive stress testing plan to validate this platform can reliably handle the agency client's volume requirements.
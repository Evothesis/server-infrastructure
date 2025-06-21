# Database Schema Documentation

This directory contains the complete database schema for the analytics platform, organized as incremental SQL files that are executed in order during PostgreSQL initialization.

## 📁 File Structure

```
database/
├── 01_init.sql          # Core event collection schema
├── 02_analytics.sql     # Analytics processing tables
├── 03_procedures.sql    # ETL procedures and functions (future)
└── README.md           # This documentation
```

## 🗃️ Schema Overview

### Data Flow Architecture

```
Raw Events (tracking.js) 
       ↓
┌─────────────────┐
│   events_log    │ ← Raw JSONB storage
│   (01_init.sql) │
└─────────────────┘
       ↓ ETL Process
┌─────────────────┐
│ Analytics Tables│ ← Structured, queryable data
│ (02_analytics)  │
└─────────────────┘
       ↓ Aggregation
┌─────────────────┐
│ Daily Metrics   │ ← Pre-computed summaries
│ (02_analytics)  │
└─────────────────┘
```

## 📊 Core Tables (01_init.sql)

### `events_log`
Primary table for raw event storage with JSONB flexibility and extracted core fields for performance.

```sql
CREATE TABLE events_log (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,           -- 'pageview', 'click', 'batch', etc.
    session_id VARCHAR(100),                   -- User session identifier
    visitor_id VARCHAR(100),                   -- Anonymous visitor identifier
    site_id VARCHAR(100),                      -- Multi-tenant site separation
    timestamp TIMESTAMPTZ NOT NULL,            -- Event occurrence time
    url TEXT,                                  -- Page URL where event occurred
    path VARCHAR(500),                         -- URL path component
    user_agent TEXT,                           -- Browser user agent string
    ip_address INET,                           -- Client IP address
    raw_event_data JSONB NOT NULL,            -- Complete event payload
    created_at TIMESTAMPTZ DEFAULT NOW(),     -- Record creation time
    processed_at TIMESTAMPTZ                  -- ETL processing timestamp
);
```

**Key Features:**
- **JSONB Storage**: Flexible event data storage with efficient querying
- **Extracted Fields**: Core fields for fast filtering and indexing
- **Time-Series Optimized**: Indexed by timestamp for chronological queries
- **Multi-Tenant**: Site-based data separation
- **Processing Tracking**: `processed_at` field for ETL pipeline management

**Indexes:**
```sql
CREATE INDEX idx_events_log_timestamp ON events_log(timestamp);
CREATE INDEX idx_events_log_site_created ON events_log(site_id, created_at);
CREATE INDEX idx_events_log_session ON events_log(session_id);
CREATE INDEX idx_events_log_event_type ON events_log(event_type);
CREATE INDEX idx_events_log_processed ON events_log(processed_at);
CREATE INDEX idx_events_log_raw_data_gin ON events_log USING gin(raw_event_data);
```

## 📈 Analytics Tables (02_analytics.sql)

### `user_sessions`
Aggregated session data with complete attribution and device information.

```sql
CREATE TABLE user_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    visitor_id VARCHAR(100) NOT NULL,
    site_id VARCHAR(100) NOT NULL,
    
    -- Session timing
    session_start TIMESTAMPTZ NOT NULL,
    session_end TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Session metrics
    pageview_count INTEGER DEFAULT 0,
    event_count INTEGER DEFAULT 0,
    bounce BOOLEAN DEFAULT TRUE,
    
    -- Entry/exit page tracking
    entry_url TEXT,
    entry_path VARCHAR(500),
    entry_title TEXT,
    exit_url TEXT,
    exit_path VARCHAR(500),
    
    -- Attribution data
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),
    utm_term VARCHAR(100),
    referrer_type VARCHAR(50),
    referrer_platform VARCHAR(100),
    original_referrer TEXT,
    
    -- Device/browser data
    user_agent TEXT,
    browser_language VARCHAR(10),
    timezone VARCHAR(50),
    screen_width INTEGER,
    screen_height INTEGER,
    viewport_width INTEGER,
    viewport_height INTEGER,
    device_pixel_ratio DECIMAL(3,2)
);
```

**Purpose:** Central table for session analytics, attribution analysis, and user journey tracking.

### `pageviews`
Individual page view records with timing and referrer information.

```sql
CREATE TABLE pageviews (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    visitor_id VARCHAR(100) NOT NULL,
    site_id VARCHAR(100) NOT NULL,
    
    -- Page metadata
    url TEXT NOT NULL,
    path VARCHAR(500) NOT NULL,
    title TEXT,
    query_params TEXT,
    hash_fragment VARCHAR(500),
    
    -- Timing data
    view_timestamp TIMESTAMPTZ NOT NULL,
    time_on_page_seconds INTEGER,
    
    -- Referrer tracking
    referrer TEXT,
    internal_referrer BOOLEAN DEFAULT FALSE,
    
    -- Attribution (can override session-level attribution)
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),
    utm_term VARCHAR(100)
);
```

**Purpose:** Page-level analytics, content performance, and user flow analysis.

### `user_events`
Structured storage for all user interactions with flexible event data.

```sql
CREATE TABLE user_events (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    visitor_id VARCHAR(100) NOT NULL,
    site_id VARCHAR(100) NOT NULL,
    
    -- Event identification
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    page_url TEXT,
    page_path VARCHAR(500),
    
    -- Flexible event data
    event_data JSONB,
    
    -- Extracted fields for common queries
    element_tag VARCHAR(20),        -- Click events
    element_classes TEXT,           -- Click events
    element_id VARCHAR(100),        -- Click events
    scroll_percentage INTEGER,      -- Scroll events
    form_id VARCHAR(100)           -- Form events
);
```

**Supported Event Types:**
- `click` - Element clicks with tag, class, ID information
- `scroll` - Scroll position tracking
- `scroll_depth` - Milestone achievements (25%, 50%, 75%, 100%)
- `form_submit` - Form submission events
- `text_copy` - Text selection and copy events
- `page_visibility` - Tab focus/blur tracking

### `form_submissions`
Dedicated table for form analytics with structured field data.

```sql
CREATE TABLE form_submissions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    visitor_id VARCHAR(100) NOT NULL,
    site_id VARCHAR(100) NOT NULL,
    
    -- Form metadata
    form_id VARCHAR(100),
    form_action TEXT,
    form_method VARCHAR(10),
    page_url TEXT,
    page_path VARCHAR(500),
    
    -- Submission details
    submit_timestamp TIMESTAMPTZ NOT NULL,
    field_count INTEGER,
    form_data JSONB              -- Sensitive fields automatically redacted
);
```

**Privacy Features:**
- Automatic redaction of sensitive fields (passwords, credit cards, SSNs)
- Configurable field filtering
- Form completion rate analysis

### `daily_site_metrics`
Pre-aggregated daily statistics for fast dashboard queries.

```sql
CREATE TABLE daily_site_metrics (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(100) NOT NULL,
    metric_date DATE NOT NULL,
    
    -- Core metrics
    unique_visitors INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_pageviews INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,4),
    
    -- Engagement metrics
    avg_session_duration_seconds INTEGER,
    avg_pages_per_session DECIMAL(8,2),
    total_events INTEGER DEFAULT 0,
    
    -- Traffic source breakdown
    direct_sessions INTEGER DEFAULT 0,
    search_sessions INTEGER DEFAULT 0,
    social_sessions INTEGER DEFAULT 0,
    referral_sessions INTEGER DEFAULT 0,
    
    UNIQUE(site_id, metric_date)
);
```

**Purpose:** High-performance dashboard queries, trend analysis, and reporting.

## 👁️ Analytics Views

### `active_sessions`
Real-time view of currently active sessions (last 30 minutes).

```sql
CREATE VIEW active_sessions AS
SELECT s.*, (NOW() - s.session_start) as session_age
FROM user_sessions s 
WHERE s.session_end IS NULL 
AND s.session_start > NOW() - INTERVAL '30 minutes';
```

### `page_performance`
Page-level performance metrics including bounce rates and time on page.

```sql
CREATE VIEW page_performance AS
SELECT 
    site_id,
    path,
    COUNT(*) as total_views,
    AVG(time_on_page_seconds) as avg_time_on_page,
    COUNT(DISTINCT session_id) as unique_sessions,
    SUM(CASE WHEN time_on_page_seconds < 10 THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) as bounce_rate
FROM pageviews 
WHERE view_timestamp > NOW() - INTERVAL '30 days'
GROUP BY site_id, path;
```

### `traffic_sources`
Traffic source analysis with session metrics by referrer type.

```sql
CREATE VIEW traffic_sources AS
SELECT 
    site_id,
    referrer_type,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    AVG(duration_seconds) as avg_session_duration,
    AVG(pageview_count) as avg_pages_per_session
FROM user_sessions 
WHERE session_start > NOW() - INTERVAL '30 days'
GROUP BY site_id, referrer_type;
```

## 🔄 ETL Pipeline (Future: 03_procedures.sql)

### Processing Flow

1. **Raw Event Processing** (`events_log` → Analytics Tables)
   - Extract pageviews from `pageview` events
   - Process batched events into individual `user_events`
   - Create/update sessions based on session lifecycle
   - Calculate time-on-page from sequential pageviews

2. **Session Aggregation**
   - Update session metrics (duration, page count, bounce status)
   - Calculate exit pages and session completion
   - Aggregate event counts per session

3. **Daily Metrics Calculation**
   - Roll up session data into daily summaries
   - Calculate bounce rates, average session duration
   - Segment traffic by source type

### Planned Stored Procedures

```sql
-- Process new events from events_log
CALL process_events_batch(batch_size := 1000);

-- Update session metrics for incomplete sessions
CALL update_active_sessions();

-- Generate daily metrics for specified date range
CALL calculate_daily_metrics(start_date := '2025-06-01', end_date := '2025-06-30');

-- Clean up old processed events
CALL cleanup_processed_events(retention_days := 90);
```

## 📊 Sample Queries

### Session Analysis
```sql
-- Top pages by unique visitors (last 7 days)
SELECT 
    path,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    COUNT(*) as total_pageviews,
    AVG(time_on_page_seconds) as avg_time_on_page
FROM pageviews 
WHERE view_timestamp > NOW() - INTERVAL '7 days'
GROUP BY path 
ORDER BY unique_visitors DESC 
LIMIT 10;
```

### Conversion Funnel
```sql
-- Form conversion funnel
WITH funnel AS (
    SELECT 
        session_id,
        BOOL_OR(path = '/products.html') as viewed_products,
        BOOL_OR(path = '/contact.html') as viewed_contact,
        BOOL_OR(event_type = 'form_submit') as submitted_form
    FROM pageviews p
    LEFT JOIN user_events e USING (session_id)
    WHERE p.view_timestamp > NOW() - INTERVAL '30 days'
    GROUP BY session_id
)
SELECT 
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE viewed_products) as products_viewers,
    COUNT(*) FILTER (WHERE viewed_contact) as contact_viewers,
    COUNT(*) FILTER (WHERE submitted_form) as form_submitters,
    
    -- Conversion rates
    COUNT(*) FILTER (WHERE viewed_contact)::DECIMAL / COUNT(*) as contact_rate,
    COUNT(*) FILTER (WHERE submitted_form)::DECIMAL / COUNT(*) FILTER (WHERE viewed_contact) as form_conversion_rate
FROM funnel;
```

### Traffic Source Performance
```sql
-- Attribution analysis by UTM campaign
SELECT 
    utm_source,
    utm_medium,
    utm_campaign,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    AVG(duration_seconds) as avg_session_duration,
    AVG(pageview_count) as avg_pages_per_session,
    AVG(CASE WHEN bounce THEN 1 ELSE 0 END) as bounce_rate
FROM user_sessions 
WHERE session_start > NOW() - INTERVAL '30 days'
    AND utm_source IS NOT NULL
GROUP BY utm_source, utm_medium, utm_campaign
ORDER BY sessions DESC;
```

## 🔧 Maintenance

### Regular Maintenance Tasks

**Daily:**
```sql
-- Process recent events
CALL process_events_batch(5000);

-- Update daily metrics for yesterday
CALL calculate_daily_metrics(
    start_date := CURRENT_DATE - 1,
    end_date := CURRENT_DATE - 1
);
```

**Weekly:**
```sql
-- Cleanup old processed events (keep 90 days)
CALL cleanup_processed_events(90);

-- Update table statistics
ANALYZE events_log;
ANALYZE user_sessions;
ANALYZE pageviews;
ANALYZE user_events;
```

**Monthly:**
```sql
-- Rebuild indexes for optimal performance
REINDEX TABLE events_log;
REINDEX TABLE pageviews;

-- Vacuum to reclaim space
VACUUM ANALYZE;
```

### Performance Monitoring

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check index usage
SELECT 
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

## 🚨 Troubleshooting

### Common Issues

**High disk usage**
```sql
-- Check largest tables
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename) DESC;

-- Clean up old events
DELETE FROM events_log 
WHERE created_at < NOW() - INTERVAL '90 days' 
AND processed_at IS NOT NULL;
```

**Slow queries**
```sql
-- Check for missing indexes
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename IN ('events_log', 'pageviews', 'user_sessions')
ORDER BY tablename, attname;

-- Enable query logging temporarily
SET log_statement = 'all';
SET log_min_duration_statement = 1000; -- Log queries > 1 second
```

**ETL processing delays**
```sql
-- Check unprocessed events
SELECT 
    event_type,
    COUNT(*) as unprocessed_count,
    MIN(created_at) as oldest_unprocessed
FROM events_log 
WHERE processed_at IS NULL
GROUP BY event_type;

-- Process backlog
CALL process_events_batch(10000);
```

## 📋 Schema Migration Guide

### Adding New Event Types

1. **Update tracking pixel** to send new event type
2. **No schema changes needed** - JSONB storage handles new event structures
3. **Add ETL processing** for new event type if structured analytics needed
4. **Create new analytics table** if event type requires specialized storage

### Schema Version Updates

1. **Create new migration file** (e.g., `04_new_feature.sql`)
2. **Include rollback instructions** in comments
3. **Test on development data** before production
4. **Update this documentation** with new schema elements

### Backup and Recovery

```bash
# Backup entire database
docker-compose exec postgres pg_dump -U postgres postgres > backup.sql

# Backup specific tables
docker-compose exec postgres pg_dump -U postgres -t events_log postgres > events_backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U postgres postgres < backup.sql
```

---

**For technical questions about the database schema, please refer to the main project documentation or create an issue with the `database` label.**
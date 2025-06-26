# Database Schema Documentation

This directory contains the database schema for the data-as-a-service analytics platform, designed for raw event collection and S3 export rather than complex analytics processing.

## 📁 File Structure

```
database/
├── 01_init.sql          # Core event collection schema
└── README.md           # This documentation
```

## 🗃️ Schema Overview

### Simplified Data Flow Architecture

```
Raw Events (tracking.js) 
       ↓
┌─────────────────┐
│   events_log    │ ← Raw JSONB storage
│   (01_init.sql) │
└─────────────────┘
       ↓ S3 Export
┌─────────────────┐
│ Client S3 Bucket│ ← Complete data ownership
│ + Backup Bucket │
└─────────────────┘
```

**Design Philosophy:**
- **Raw Events Only**: No processed analytics tables
- **JSONB Flexibility**: Handle any event structure without schema changes
- **Export-Focused**: Optimized for batch export operations
- **Client Ownership**: Complete data export, no vendor lock-in

## 📊 Core Table (01_init.sql)

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
    exported_at TIMESTAMPTZ                   -- S3 export timestamp
);
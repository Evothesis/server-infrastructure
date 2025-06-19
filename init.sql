-- Create the events log table
CREATE TABLE IF NOT EXISTS events_log (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    visitor_id VARCHAR(100),
    site_id VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL,
    url TEXT,
    path VARCHAR(500),
    user_agent TEXT,
    ip_address INET,
    raw_event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_log_timestamp ON events_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_log_site_created ON events_log(site_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_log_session ON events_log(session_id);
CREATE INDEX IF NOT EXISTS idx_events_log_event_type ON events_log(event_type);
CREATE INDEX IF NOT EXISTS idx_events_log_processed ON events_log(processed_at);

-- JSONB indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_log_raw_data_gin ON events_log USING gin(raw_event_data);
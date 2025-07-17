-- Create the events log table with complete client attribution and constraints
CREATE TABLE IF NOT EXISTS events_log (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid() NOT NULL,  -- FIXED: Added NOT NULL constraint
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
    processed_at TIMESTAMPTZ,
    client_id VARCHAR(255),           -- FIXED: Added client attribution column
    batch_id UUID,                    -- FIXED: Added missing batch_id referenced in README
    export_status VARCHAR(20) DEFAULT 'pending'  -- FIXED: Added missing export_status column
);

-- Create indexes for common queries (matching SQLAlchemy expectations)
CREATE INDEX IF NOT EXISTS idx_events_log_timestamp ON events_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_log_site_created ON events_log(site_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_log_session ON events_log(session_id);
CREATE INDEX IF NOT EXISTS idx_events_log_event_type ON events_log(event_type);
CREATE INDEX IF NOT EXISTS idx_events_log_processed ON events_log(processed_at);
CREATE INDEX IF NOT EXISTS idx_events_log_client_id ON events_log(client_id);
CREATE INDEX IF NOT EXISTS idx_events_log_visitor_id ON events_log(visitor_id);  -- FIXED: Added missing index
CREATE INDEX IF NOT EXISTS idx_events_log_created_at ON events_log(created_at);  -- FIXED: Added missing index
CREATE INDEX IF NOT EXISTS idx_events_log_batch_id ON events_log(batch_id);      -- FIXED: Added batch index
CREATE INDEX IF NOT EXISTS idx_events_log_export_status ON events_log(export_status);  -- FIXED: Added export index

-- JSONB indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_log_raw_data_gin ON events_log USING gin(raw_event_data);
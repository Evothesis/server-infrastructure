-- 1. SESSIONS TABLE - One record per user session
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(200) PRIMARY KEY,
    visitor_id VARCHAR(200) NOT NULL,
    site_id VARCHAR(200) NOT NULL,
    
    -- Session timing
    session_start TIMESTAMPTZ NOT NULL,
    session_end TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Session metrics
    pageview_count INTEGER DEFAULT 0,
    event_count INTEGER DEFAULT 0,
    bounce BOOLEAN DEFAULT TRUE, -- Single page session
    
    -- Entry page data
    entry_url TEXT,
    entry_path VARCHAR(500),
    entry_title TEXT,
    
    -- Exit page data  
    exit_url TEXT,
    exit_path VARCHAR(500),
    
    -- Attribution (from first pageview)
    utm_source VARCHAR(500),
    utm_medium VARCHAR(500), 
    utm_campaign VARCHAR(500),
    utm_content VARCHAR(500),
    utm_term VARCHAR(500),
    referrer_type VARCHAR(50), -- 'direct', 'search', 'social', 'referral', 'internal'
    referrer_platform VARCHAR(200),
    original_referrer TEXT,
    
    -- Device/browser (from first pageview)
    user_agent TEXT,
    browser_language VARCHAR(10),
    timezone VARCHAR(50),
    screen_width INTEGER,
    screen_height INTEGER,
    viewport_width INTEGER,
    viewport_height INTEGER,
    device_pixel_ratio DECIMAL(3,2),
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);-- Analytics Schema for processed events
-- Run this after the existing events_log table

-- ==================================================
-- CORE ANALYTICS TABLES
-- ==================================================

-- 1. SESSIONS TABLE - One record per user session
CREATE TABLE IF NOT EXISTS user_sessions (
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
    bounce BOOLEAN DEFAULT TRUE, -- Single page session
    
    -- Entry page data
    entry_url TEXT,
    entry_path VARCHAR(500),
    entry_title TEXT,
    
    -- Exit page data  
    exit_url TEXT,
    exit_path VARCHAR(500),
    
    -- Attribution (from first pageview)
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100), 
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),
    utm_term VARCHAR(100),
    referrer_type VARCHAR(50), -- 'direct', 'search', 'social', 'referral', 'internal'
    referrer_platform VARCHAR(100),
    original_referrer TEXT,
    
    -- Device/browser (from first pageview)
    user_agent TEXT,
    browser_language VARCHAR(10),
    timezone VARCHAR(50),
    screen_width INTEGER,
    screen_height INTEGER,
    viewport_width INTEGER,
    viewport_height INTEGER,
    device_pixel_ratio DECIMAL(3,2),
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. PAGEVIEWS TABLE - One record per page view
CREATE TABLE IF NOT EXISTS pageviews (
    id SERIAL PRIMARY KEY,
    
    -- Identifiers
    session_id VARCHAR(200) NOT NULL,
    visitor_id VARCHAR(200) NOT NULL, 
    site_id VARCHAR(200) NOT NULL,
    
    -- Page data
    url TEXT NOT NULL,
    path VARCHAR(500) NOT NULL,
    title TEXT,
    query_params TEXT,
    hash_fragment VARCHAR(500),
    
    -- Timing
    view_timestamp TIMESTAMPTZ NOT NULL,
    time_on_page_seconds INTEGER, -- Calculated from next pageview or page_exit
    
    -- Referrer for this specific pageview
    referrer TEXT,
    internal_referrer BOOLEAN DEFAULT FALSE,
    
    -- Attribution (inherited from session, but can be overridden)
    utm_source VARCHAR(500),
    utm_medium VARCHAR(500),
    utm_campaign VARCHAR(500), 
    utm_content VARCHAR(500),
    utm_term VARCHAR(500),
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. USER EVENTS TABLE - Clicks, scrolls, form submissions, etc.
CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    
    -- Identifiers  
    session_id VARCHAR(200) NOT NULL,
    visitor_id VARCHAR(200) NOT NULL,
    site_id VARCHAR(200) NOT NULL,
    
    -- Event data
    event_type VARCHAR(50) NOT NULL, -- 'click', 'scroll', 'scroll_depth', 'form_submit', 'text_copy', 'page_visibility'
    event_timestamp TIMESTAMPTZ NOT NULL,
    
    -- Page context
    page_url TEXT,
    page_path VARCHAR(500),
    
    -- Event details (flexible JSON for different event types)
    event_data JSONB,
    
    -- Common extracted fields for fast querying
    element_tag VARCHAR(20), -- For clicks
    element_classes TEXT,    -- For clicks
    element_id VARCHAR(100), -- For clicks
    scroll_percentage INTEGER, -- For scroll events
    form_id VARCHAR(100),    -- For form events
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. FORM SUBMISSIONS TABLE - Dedicated table for form analysis
CREATE TABLE IF NOT EXISTS form_submissions (
    id SERIAL PRIMARY KEY,
    
    -- Identifiers
    session_id VARCHAR(200) NOT NULL,
    visitor_id VARCHAR(200) NOT NULL,
    site_id VARCHAR(200) NOT NULL,
    
    -- Form data
    form_id VARCHAR(100),
    form_action TEXT,
    form_method VARCHAR(10),
    page_url TEXT,
    page_path VARCHAR(500),
    
    -- Submission details
    submit_timestamp TIMESTAMPTZ NOT NULL,
    field_count INTEGER,
    form_data JSONB, -- Store form fields (with sensitive data redacted)
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. DAILY SITE METRICS - Pre-aggregated daily stats
CREATE TABLE IF NOT EXISTS daily_site_metrics (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(100) NOT NULL,
    metric_date DATE NOT NULL,
    
    -- Visitor metrics
    unique_visitors INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_pageviews INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,4), -- Percentage as decimal (e.g., 0.3456 = 34.56%)
    
    -- Engagement metrics
    avg_session_duration_seconds INTEGER,
    avg_pages_per_session DECIMAL(8,2),
    total_events INTEGER DEFAULT 0,
    
    -- Traffic source breakdown
    direct_sessions INTEGER DEFAULT 0,
    search_sessions INTEGER DEFAULT 0,
    social_sessions INTEGER DEFAULT 0,
    referral_sessions INTEGER DEFAULT 0,
    
    -- Processing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(site_id, metric_date)
);

-- ==================================================
-- INDEXES FOR PERFORMANCE
-- ==================================================

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON user_sessions(visitor_id);
CREATE INDEX IF NOT EXISTS idx_sessions_site_start ON user_sessions(site_id, session_start);
CREATE INDEX IF NOT EXISTS idx_sessions_attribution ON user_sessions(utm_source, utm_medium, utm_campaign);

-- Pageviews indexes  
CREATE INDEX IF NOT EXISTS idx_pageviews_session ON pageviews(session_id);
CREATE INDEX IF NOT EXISTS idx_pageviews_site_timestamp ON pageviews(site_id, view_timestamp);
CREATE INDEX IF NOT EXISTS idx_pageviews_path ON pageviews(site_id, path);

-- User events indexes
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_type_timestamp ON user_events(event_type, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_user_events_site_timestamp ON user_events(site_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_user_events_data_gin ON user_events USING gin(event_data);

-- Form submissions indexes
CREATE INDEX IF NOT EXISTS idx_form_submissions_session ON form_submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_site_timestamp ON form_submissions(site_id, submit_timestamp);

-- Daily metrics indexes
CREATE INDEX IF NOT EXISTS idx_daily_metrics_site_date ON daily_site_metrics(site_id, metric_date);

-- ==================================================
-- HELPER VIEWS FOR COMMON QUERIES
-- ==================================================

-- View: Current active sessions (last 30 minutes)
CREATE OR REPLACE VIEW active_sessions AS
SELECT 
    s.*,
    (NOW() - s.session_start) as session_age
FROM user_sessions s 
WHERE s.session_end IS NULL 
AND s.session_start > NOW() - INTERVAL '30 minutes';

-- View: Page performance (avg time on page, bounce rate by page)
CREATE OR REPLACE VIEW page_performance AS
SELECT 
    site_id,
    path,
    COUNT(*) as total_views,
    AVG(time_on_page_seconds) as avg_time_on_page,
    COUNT(DISTINCT session_id) as unique_sessions,
    SUM(CASE WHEN time_on_page_seconds < 10 THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) as bounce_rate
FROM pageviews 
WHERE view_timestamp > NOW() - INTERVAL '30 days'
GROUP BY site_id, path
ORDER BY total_views DESC;

-- View: Traffic sources summary
CREATE OR REPLACE VIEW traffic_sources AS
SELECT 
    site_id,
    referrer_type,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    AVG(duration_seconds) as avg_session_duration,
    AVG(pageview_count) as avg_pages_per_session
FROM user_sessions 
WHERE session_start > NOW() - INTERVAL '30 days'
GROUP BY site_id, referrer_type
ORDER BY sessions DESC;
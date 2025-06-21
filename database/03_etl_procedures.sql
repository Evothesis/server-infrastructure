-- ETL Procedures for Analytics Pipeline
-- File: database/03_etl_procedures.sql
-- Purpose: Transform raw events_log data into structured analytics tables

-- ==================================================
-- UTILITY FUNCTIONS
-- ==================================================

-- Function to safely extract JSONB values with defaults
CREATE OR REPLACE FUNCTION safe_jsonb_text(data JSONB, path TEXT, default_val TEXT DEFAULT NULL)
RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE((data ->> path), default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to safely extract JSONB integer values
CREATE OR REPLACE FUNCTION safe_jsonb_int(data JSONB, path TEXT, default_val INTEGER DEFAULT NULL)
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE((data ->> path)::INTEGER, default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to safely extract nested JSONB values
CREATE OR REPLACE FUNCTION safe_jsonb_nested_text(data JSONB, path1 TEXT, path2 TEXT, default_val TEXT DEFAULT NULL)
RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE((data -> path1 ->> path2), default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ==================================================
-- MAIN ETL PROCEDURES
-- ==================================================

-- Process pageview events into structured tables
CREATE OR REPLACE FUNCTION process_pageview_events(batch_size INTEGER DEFAULT 1000)
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    rec RECORD;
BEGIN
    FOR rec IN 
        SELECT * FROM events_log 
        WHERE event_type = 'pageview' 
        AND processed_at IS NULL 
        ORDER BY created_at 
        LIMIT batch_size
    LOOP
        -- Create or update session record
        INSERT INTO user_sessions (
            session_id, visitor_id, site_id, session_start,
            entry_url, entry_path, entry_title,
            utm_source, utm_medium, utm_campaign, utm_content, utm_term,
            referrer_type, referrer_platform, original_referrer,
            user_agent, browser_language, timezone,
            screen_width, screen_height, viewport_width, viewport_height, device_pixel_ratio
        )
        VALUES (
            COALESCE(rec.session_id, 'unknown'),
            COALESCE(rec.visitor_id, 'unknown'),
            COALESCE(rec.site_id, 'unknown'),
            rec.timestamp,
            rec.url,
            rec.path,
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'title'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_source'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_medium'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_campaign'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_content'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_term'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'referrerType'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'referrerPlatform'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'referrer'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'browser', 'userAgent'), ''),
            COALESCE(LEFT(safe_jsonb_nested_text(rec.raw_event_data, 'browser', 'language'), 10), 'en'),
            COALESCE(LEFT(safe_jsonb_nested_text(rec.raw_event_data, 'browser', 'timezone'), 50), 'UTC'),
            COALESCE(safe_jsonb_int(rec.raw_event_data -> 'browser', 'screenWidth'), 0),
            COALESCE(safe_jsonb_int(rec.raw_event_data -> 'browser', 'screenHeight'), 0),
            COALESCE(safe_jsonb_int(rec.raw_event_data -> 'browser', 'viewportWidth'), 0),
            COALESCE(safe_jsonb_int(rec.raw_event_data -> 'browser', 'viewportHeight'), 0),
            COALESCE(safe_jsonb_int(rec.raw_event_data -> 'browser', 'devicePixelRatio'), 1)::DECIMAL(3,2)
        )
        ON CONFLICT (session_id) DO UPDATE SET
            updated_at = NOW(),
            entry_url = CASE WHEN user_sessions.session_start > rec.timestamp THEN rec.url ELSE user_sessions.entry_url END,
            entry_path = CASE WHEN user_sessions.session_start > rec.timestamp THEN rec.path ELSE user_sessions.entry_path END,
            entry_title = CASE WHEN user_sessions.session_start > rec.timestamp 
                             THEN COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'title'), '')
                             ELSE user_sessions.entry_title END,
            session_start = LEAST(user_sessions.session_start, rec.timestamp);

        -- Insert pageview record
        INSERT INTO pageviews (
            session_id, visitor_id, site_id, url, path, title,
            query_params, hash_fragment, view_timestamp, referrer, internal_referrer,
            utm_source, utm_medium, utm_campaign, utm_content, utm_term
        )
        VALUES (
            COALESCE(rec.session_id, 'unknown'),
            COALESCE(rec.visitor_id, 'unknown'),
            COALESCE(rec.site_id, 'unknown'),
            COALESCE(rec.url, ''),
            COALESCE(rec.path, '/'),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'title'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'queryParams'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'hash'), ''),
            rec.timestamp,
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'page', 'referrer'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'referrerType'), '') = 'internal',
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_source'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_medium'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_campaign'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_content'), ''),
            COALESCE(safe_jsonb_nested_text(rec.raw_event_data, 'attribution', 'utmParams', 'utm_term'), '')
        );

        -- Mark as processed
        UPDATE events_log SET processed_at = NOW() WHERE id = rec.id;
        processed_count := processed_count + 1;
    END LOOP;

    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Process page_exit events to calculate time on page
CREATE OR REPLACE FUNCTION process_page_exit_events(batch_size INTEGER DEFAULT 1000)
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    rec RECORD;
    time_spent INTEGER;
BEGIN
    FOR rec IN 
        SELECT * FROM events_log 
        WHERE event_type = 'page_exit' 
        AND processed_at IS NULL 
        ORDER BY created_at 
        LIMIT batch_size
    LOOP
        -- Extract time spent from event data
        time_spent := safe_jsonb_int(rec.raw_event_data -> 'eventData', 'timeSpent');
        IF time_spent IS NOT NULL THEN
            time_spent := time_spent / 1000; -- Convert ms to seconds
        END IF;

        -- Update the most recent pageview for this session/path with time on page
        UPDATE pageviews 
        SET time_on_page_seconds = time_spent
        WHERE session_id = rec.session_id 
        AND path = rec.path
        AND view_timestamp = (
            SELECT MAX(view_timestamp) 
            FROM pageviews p2 
            WHERE p2.session_id = rec.session_id 
            AND p2.path = rec.path
            AND p2.view_timestamp <= rec.timestamp
        );

        -- Update session exit data
        UPDATE user_sessions 
        SET 
            session_end = rec.timestamp,
            exit_url = rec.url,
            exit_path = rec.path,
            updated_at = NOW()
        WHERE session_id = rec.session_id
        AND (session_end IS NULL OR session_end < rec.timestamp);

        -- Mark as processed
        UPDATE events_log SET processed_at = NOW() WHERE id = rec.id;
        processed_count := processed_count + 1;
    END LOOP;

    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Process batch events into individual user_events
CREATE OR REPLACE FUNCTION process_batch_events(batch_size INTEGER DEFAULT 1000)
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    batch_rec RECORD;
    event_item JSONB;
    event_data JSONB;
    event_type_val TEXT;
    event_timestamp_val TIMESTAMPTZ;
BEGIN
    FOR batch_rec IN 
        SELECT * FROM events_log 
        WHERE event_type = 'batch' 
        AND processed_at IS NULL 
        ORDER BY created_at 
        LIMIT batch_size
    LOOP
        -- Process each event in the batch
        FOR event_item IN 
            SELECT jsonb_array_elements(batch_rec.raw_event_data -> 'events')
        LOOP
            event_type_val := event_item ->> 'eventType';
            event_timestamp_val := (event_item ->> 'timestamp')::TIMESTAMPTZ;
            event_data := event_item -> 'eventData';

            -- Insert individual event
            INSERT INTO user_events (
                session_id, visitor_id, site_id, event_type, event_timestamp,
                page_url, page_path, event_data,
                scroll_percentage, element_tag, element_classes, element_id
            )
            VALUES (
                COALESCE(batch_rec.session_id, 'unknown'),
                COALESCE(batch_rec.visitor_id, 'unknown'),
                COALESCE(batch_rec.site_id, 'unknown'),
                COALESCE(event_type_val, 'unknown'),
                event_timestamp_val,
                batch_rec.url,
                batch_rec.path,
                event_data,
                safe_jsonb_int(event_data, 'scrollPercentage'),
                safe_jsonb_text(event_data, 'tagName'),
                safe_jsonb_text(event_data, 'classes'),
                safe_jsonb_text(event_data, 'id')
            );
        END LOOP;

        -- Mark as processed
        UPDATE events_log SET processed_at = NOW() WHERE id = batch_rec.id;
        processed_count := processed_count + 1;
    END LOOP;

    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Process form_submit events
CREATE OR REPLACE FUNCTION process_form_submit_events(batch_size INTEGER DEFAULT 1000)
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    rec RECORD;
    form_data_json JSONB;
    field_count_val INTEGER;
BEGIN
    FOR rec IN 
        SELECT * FROM events_log 
        WHERE event_type = 'form_submit' 
        AND processed_at IS NULL 
        ORDER BY created_at 
        LIMIT batch_size
    LOOP
        form_data_json := rec.raw_event_data -> 'eventData' -> 'formData';
        
        -- Calculate field count safely
        BEGIN
            SELECT array_length(array(SELECT jsonb_object_keys(form_data_json)), 1) INTO field_count_val;
        EXCEPTION WHEN OTHERS THEN
            field_count_val := 0;
        END;

        -- Insert form submission record
        INSERT INTO form_submissions (
            session_id, visitor_id, site_id, form_id, form_action, form_method,
            page_url, page_path, submit_timestamp, field_count, form_data
        )
        VALUES (
            COALESCE(rec.session_id, 'unknown'),
            COALESCE(rec.visitor_id, 'unknown'),
            COALESCE(rec.site_id, 'unknown'),
            safe_jsonb_nested_text(rec.raw_event_data, 'eventData', 'formId'),
            safe_jsonb_nested_text(rec.raw_event_data, 'eventData', 'formAction'),
            safe_jsonb_nested_text(rec.raw_event_data, 'eventData', 'formMethod'),
            rec.url,
            rec.path,
            rec.timestamp,
            field_count_val,
            form_data_json
        );

        -- Also add to user_events for general event tracking
        INSERT INTO user_events (
            session_id, visitor_id, site_id, event_type, event_timestamp,
            page_url, page_path, event_data, form_id
        )
        VALUES (
            COALESCE(rec.session_id, 'unknown'),
            COALESCE(rec.visitor_id, 'unknown'),
            COALESCE(rec.site_id, 'unknown'),
            'form_submit',
            rec.timestamp,
            rec.url,
            rec.path,
            rec.raw_event_data -> 'eventData',
            safe_jsonb_nested_text(rec.raw_event_data, 'eventData', 'formId')
        );

        -- Mark as processed
        UPDATE events_log SET processed_at = NOW() WHERE id = rec.id;
        processed_count := processed_count + 1;
    END LOOP;

    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- ==================================================
-- MASTER ETL PROCEDURE
-- ==================================================

-- Main ETL procedure that processes all event types
CREATE OR REPLACE FUNCTION run_etl_pipeline(batch_size INTEGER DEFAULT 1000)
RETURNS TABLE(
    step_name TEXT,
    records_processed INTEGER,
    execution_time INTERVAL
) AS $$
DECLARE
    start_time TIMESTAMPTZ;
    step_result INTEGER;
BEGIN
    -- Process page exit events
    start_time := clock_timestamp();
    SELECT process_page_exit_events(batch_size) INTO step_result;
    RETURN QUERY SELECT 'process_page_exit_events'::TEXT, step_result, clock_timestamp() - start_time;

    -- Process batch events
    start_time := clock_timestamp();
    SELECT process_batch_events(batch_size) INTO step_result;
    RETURN QUERY SELECT 'process_batch_events'::TEXT, step_result, clock_timestamp() - start_time;

    -- Process form submit events
    start_time := clock_timestamp();
    SELECT process_form_submit_events(batch_size) INTO step_result;
    RETURN QUERY SELECT 'process_form_submit_events'::TEXT, step_result, clock_timestamp() - start_time;
END;
$ LANGUAGE plpgsql;

-- ==================================================
-- CLEANUP PROCEDURES
-- ==================================================

-- Clean up old processed events
CREATE OR REPLACE FUNCTION cleanup_processed_events(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM events_log 
    WHERE processed_at IS NOT NULL 
    AND processed_at < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$ LANGUAGE plpgsql;

-- Calculate daily metrics for a specific date
CREATE OR REPLACE FUNCTION calculate_daily_metrics(target_date DATE DEFAULT CURRENT_DATE - 1)
RETURNS INTEGER AS $
DECLARE
    site_rec RECORD;
    metrics_count INTEGER := 0;
    unique_visitors_count INTEGER;
    total_sessions_count INTEGER;
    total_pageviews_count INTEGER;
    bounce_rate_calc DECIMAL(5,4);
    avg_duration INTEGER;
    avg_pages DECIMAL(8,2);
    total_events_count INTEGER;
    direct_count INTEGER;
    search_count INTEGER;
    social_count INTEGER;
    referral_count INTEGER;
BEGIN
    FOR site_rec IN 
        SELECT DISTINCT site_id 
        FROM user_sessions 
        WHERE DATE(session_start) = target_date
    LOOP
        -- Calculate metrics for this site
        SELECT COUNT(DISTINCT visitor_id) INTO unique_visitors_count
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date;

        SELECT COUNT(*) INTO total_sessions_count
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date;

        SELECT COUNT(*) INTO total_pageviews_count
        FROM pageviews 
        WHERE site_id = site_rec.site_id 
        AND DATE(view_timestamp) = target_date;

        SELECT AVG(CASE WHEN bounce THEN 1 ELSE 0 END) INTO bounce_rate_calc
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date;

        SELECT AVG(duration_seconds) INTO avg_duration
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date
        AND duration_seconds IS NOT NULL;

        SELECT AVG(pageview_count) INTO avg_pages
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date;

        SELECT COUNT(*) INTO total_events_count
        FROM user_events 
        WHERE site_id = site_rec.site_id 
        AND DATE(event_timestamp) = target_date;

        -- Calculate traffic source breakdown
        SELECT 
            COUNT(*) FILTER (WHERE referrer_type = 'direct' OR referrer_type IS NULL OR referrer_type = ''),
            COUNT(*) FILTER (WHERE referrer_type = 'search'),
            COUNT(*) FILTER (WHERE referrer_type = 'social'),
            COUNT(*) FILTER (WHERE referrer_type = 'referral')
        INTO direct_count, search_count, social_count, referral_count
        FROM user_sessions 
        WHERE site_id = site_rec.site_id 
        AND DATE(session_start) = target_date;

        -- Insert or update daily metrics
        INSERT INTO daily_site_metrics (
            site_id, metric_date, unique_visitors, total_sessions, total_pageviews,
            bounce_rate, avg_session_duration_seconds, avg_pages_per_session, total_events,
            direct_sessions, search_sessions, social_sessions, referral_sessions
        )
        VALUES (
            site_rec.site_id, target_date, unique_visitors_count, total_sessions_count, total_pageviews_count,
            bounce_rate_calc, avg_duration, avg_pages, total_events_count,
            direct_count, search_count, social_count, referral_count
        )
        ON CONFLICT (site_id, metric_date) DO UPDATE SET
            unique_visitors = EXCLUDED.unique_visitors,
            total_sessions = EXCLUDED.total_sessions,
            total_pageviews = EXCLUDED.total_pageviews,
            bounce_rate = EXCLUDED.bounce_rate,
            avg_session_duration_seconds = EXCLUDED.avg_session_duration_seconds,
            avg_pages_per_session = EXCLUDED.avg_pages_per_session,
            total_events = EXCLUDED.total_events,
            direct_sessions = EXCLUDED.direct_sessions,
            search_sessions = EXCLUDED.search_sessions,
            social_sessions = EXCLUDED.social_sessions,
            referral_sessions = EXCLUDED.referral_sessions,
            updated_at = NOW();

        metrics_count := metrics_count + 1;
    END LOOP;

    RETURN metrics_count;
END;
$ LANGUAGE plpgsql;

-- ==================================================
-- USAGE EXAMPLES
-- ==================================================

-- Run the complete ETL pipeline:
-- SELECT * FROM run_etl_pipeline(1000);

-- Process specific event types:
-- SELECT process_pageview_events(500);
-- SELECT process_batch_events(500);
-- SELECT process_page_exit_events(500);
-- SELECT process_form_submit_events(500);

-- Generate daily metrics for yesterday:
-- SELECT calculate_daily_metrics(CURRENT_DATE - 1);

-- Clean up old data:
-- SELECT cleanup_processed_events(90);
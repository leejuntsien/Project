-- Set secure defaults
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_ciphers = 'HIGH:!aNULL:!MD5';
ALTER SYSTEM SET password_encryption = 'scram-sha-256';
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_error_verbosity = 'default';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_min_error_statement = 'error';

-- Set connection limits
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET superuser_reserved_connections = 3;

-- Set statement timeout (5 minutes)
ALTER SYSTEM SET statement_timeout = 300000;

-- Set idle session timeout (1 hour)
ALTER SYSTEM SET idle_in_transaction_session_timeout = 3600000;

-- Create extension for secure password hashing
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create roles with least privilege
CREATE ROLE app_user WITH LOGIN PASSWORD 'app_user_password';
CREATE ROLE readonly WITH LOGIN PASSWORD 'readonly_password';

-- Grant appropriate permissions
GRANT CONNECT ON DATABASE "Patient_data_FYP" TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

GRANT CONNECT ON DATABASE "Patient_data_FYP" TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Revoke public permissions
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

-- Create audit triggers
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, action, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'INSERT', row_to_json(NEW)::jsonb, current_user);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, action, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'UPDATE', row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb, current_user);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, action, old_data, changed_by)
        VALUES (TG_TABLE_NAME, 'DELETE', row_to_json(OLD)::jsonb, current_user);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to important tables
CREATE TRIGGER patient_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON patients
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER patient_data_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON patient_data
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER patient_trials_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON patient_trials
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Create function to clean old data periodically
CREATE OR REPLACE FUNCTION clean_old_data()
RETURNS void AS $$
BEGIN
    -- Delete live data older than 1 hour
    DELETE FROM live_patient_data
    WHERE timestamp < NOW() - INTERVAL '1 hour';
    
    -- Delete temporary trial data older than 24 hours
    DELETE FROM trial_temp
    WHERE timestamp < NOW() - INTERVAL '24 hours';
    
    -- Delete audit logs older than 90 days
    DELETE FROM audit_log
    WHERE changed_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup job
SELECT cron.schedule('clean_old_data', '0 0 * * *', 'SELECT clean_old_data();');

-- Create patients table
CREATE TABLE IF NOT EXISTS patients (
    patient_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    passkey VARCHAR(255) NOT NULL
);

-- Create admin_users table
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    passkey VARCHAR(255) NOT NULL
);

-- Create device_auth table
CREATE TABLE IF NOT EXISTS device_auth (
    device_id VARCHAR(50) PRIMARY KEY,
    secret_hash VARCHAR(255) NOT NULL,
    patient_id INTEGER NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- Create temporary table for live streaming data (unlogged for better performance)
CREATE UNLOGGED TABLE IF NOT EXISTS temp_sensor_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES device_auth(device_id) ON DELETE CASCADE
);

-- Create permanent table for trial data
CREATE TABLE IF NOT EXISTS patient_trials (
    trial_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    data_file_path VARCHAR(255),
    metadata JSONB,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES device_auth(device_id) ON DELETE CASCADE
);

-- Create patient_data table for processed trial data
CREATE TABLE IF NOT EXISTS patient_data (
    data_id SERIAL PRIMARY KEY,
    trial_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    processed_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trial_id) REFERENCES patient_trials(trial_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_temp_sensor_patient_id ON temp_sensor_data(patient_id);
CREATE INDEX IF NOT EXISTS idx_temp_sensor_timestamp ON temp_sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_patient_trials_patient_id ON patient_trials(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_data_trial_id ON patient_data(trial_id);

-- Function to clean old temporary data (runs every hour)
CREATE OR REPLACE FUNCTION cleanup_temp_data() RETURNS void AS $$
BEGIN
    DELETE FROM temp_sensor_data
    WHERE timestamp < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to clean temporary data
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule('cleanup_temp_data', '0 * * * *', 'SELECT cleanup_temp_data();');

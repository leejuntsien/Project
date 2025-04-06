-- Create unlogged table for live streaming data
CREATE UNLOGGED TABLE IF NOT EXISTS live_patient_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- Create unlogged table for temporary trial data
CREATE UNLOGGED TABLE IF NOT EXISTS trial_temp (
    id SERIAL PRIMARY KEY,
    trial_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (trial_id) REFERENCES patient_trials(trial_id) ON DELETE CASCADE
);

-- Create table for trials
CREATE TABLE IF NOT EXISTS patient_trials (
    trial_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- Create table for permanent trial data
CREATE TABLE IF NOT EXISTS patient_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    trial_id INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (trial_id) REFERENCES patient_trials(trial_id) ON DELETE CASCADE
);

-- Create indices for faster querying
CREATE INDEX IF NOT EXISTS idx_live_data_patient_id ON live_patient_data(patient_id);
CREATE INDEX IF NOT EXISTS idx_live_data_timestamp ON live_patient_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_trial_temp_trial_id ON trial_temp(trial_id);
CREATE INDEX IF NOT EXISTS idx_trial_temp_patient_id ON trial_temp(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_trials_patient_id ON patient_trials(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_data_patient_id ON patient_data(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_data_trial_id ON patient_data(trial_id);

-- Create GIN indices for JSON data
CREATE INDEX IF NOT EXISTS idx_live_data_gin ON live_patient_data USING gin (sensor_data);
CREATE INDEX IF NOT EXISTS idx_trial_temp_gin ON trial_temp USING gin (sensor_data);
CREATE INDEX IF NOT EXISTS idx_patient_data_gin ON patient_data USING gin (data);

-- Function to clean old temporary data
CREATE OR REPLACE FUNCTION cleanup_temp_data() RETURNS void AS $$
BEGIN
    -- Clean live data older than 1 hour
    DELETE FROM live_patient_data
    WHERE timestamp < NOW() - INTERVAL '1 hour';
    
    -- Clean trial temp data for completed trials
    DELETE FROM trial_temp
    WHERE trial_id IN (
        SELECT trial_id 
        FROM patient_trials 
        WHERE end_time IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to clean temporary data
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule('cleanup_temp_data', '0 * * * *', 'SELECT cleanup_temp_data();');

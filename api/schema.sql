-- Create rolling sensor data table
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- Create index for faster querying
CREATE INDEX IF NOT EXISTS idx_sensor_data_patient_id ON sensor_data(patient_id);
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp);

-- Create device authentication table
CREATE TABLE IF NOT EXISTS device_auth (
    device_id VARCHAR(50) PRIMARY KEY,
    secret_hash VARCHAR(255) NOT NULL,
    patient_id INTEGER NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS regtech_monitoring (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    structure_data JSONB,
    availability_data JSONB,
    change_analysis JSONB,
    alert_sent BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS regtech_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50),
    message TEXT,
    details JSONB,
    resolved BOOLEAN DEFAULT FALSE
);

CREATE OR REPLACE VIEW collector_regtech_credentials
WITH (security_barrier = true) AS
SELECT service_name, username, password, encrypted, enabled,
       collection_interval, last_collection, config
FROM collection_credentials
WHERE service_name = 'REGTECH';

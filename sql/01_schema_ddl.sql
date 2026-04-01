-- =============================================================================
-- AirLight Pro IoT Governance System
-- Star Schema DDL — PostgreSQL
-- Author: Alantz
-- Description: Dimensional model for L'Oréal AirLight Pro infrared hair dryer
--              telemetry data. Supports executive BI dashboards, compliance
--              reporting, and anomaly detection across global retail stores.
-- =============================================================================


-- =============================================================================
-- SCHEMA
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS airlight;
SET search_path TO airlight;


-- =============================================================================
-- DIMENSION: dim_date
-- Full date spine for time intelligence in Tableau.
-- Populated separately via Python date generator.
-- =============================================================================

CREATE TABLE dim_date (
    date_key            INT             PRIMARY KEY,  -- YYYYMMDD integer key
    full_date           DATE            NOT NULL UNIQUE,
    day_of_week         VARCHAR(10)     NOT NULL,     -- 'Monday', 'Tuesday', etc.
    day_number          SMALLINT        NOT NULL,     -- 1–7
    week_number         SMALLINT        NOT NULL,     -- ISO week 1–53
    month_number        SMALLINT        NOT NULL,     -- 1–12
    month_name          VARCHAR(10)     NOT NULL,
    quarter             SMALLINT        NOT NULL,     -- 1–4
    year                SMALLINT        NOT NULL,
    is_weekend          BOOLEAN         NOT NULL DEFAULT FALSE,
    fiscal_period       VARCHAR(7)      NOT NULL      -- 'FY2026-Q1', etc.
);

COMMENT ON TABLE dim_date IS
    'Date dimension spine. Covers 2024-01-01 through 2026-12-31 for full historical and forecast range.';


-- =============================================================================
-- DIMENSION: dim_store
-- L'Oréal retail store locations across global regions.
-- =============================================================================

CREATE TABLE dim_store (
    store_key           SERIAL          PRIMARY KEY,
    store_id            VARCHAR(20)     NOT NULL UNIQUE,  -- e.g. 'US-NYC-001'
    store_name          VARCHAR(100)    NOT NULL,
    city                VARCHAR(100)    NOT NULL,
    state_province      VARCHAR(100),
    country             VARCHAR(100)    NOT NULL,
    region              VARCHAR(50)     NOT NULL,         -- 'North America', 'EMEA', 'APAC', 'LATAM'
    store_tier          VARCHAR(20)     NOT NULL,         -- 'Flagship', 'Standard', 'Outlet'
    store_open_date     DATE            NOT NULL,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE dim_store IS
    'Retail store master. Region and tier support geographic drill-down and LOD comparisons in Tableau.';


-- =============================================================================
-- DIMENSION: dim_device
-- Individual AirLight Pro unit registry per store deployment.
-- =============================================================================

CREATE TABLE dim_device (
    device_key          SERIAL          PRIMARY KEY,
    device_id           VARCHAR(50)     NOT NULL UNIQUE,  -- e.g. 'ALP-2026-00142'
    store_key           INT             NOT NULL REFERENCES dim_store(store_key),
    model_version       VARCHAR(20)     NOT NULL,         -- 'AirLight Pro v1', 'v2', etc.
    firmware_version    VARCHAR(20)     NOT NULL,         -- 'FW-3.1.2'
    install_date        DATE            NOT NULL,
    warranty_expiry     DATE            NOT NULL,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    gdpr_masked         BOOLEAN         NOT NULL DEFAULT FALSE  -- TRUE = PII fields anonymized
);

COMMENT ON TABLE dim_device IS
    'Device registry. Each unit is tied to a store. gdpr_masked flag supports GDPR compliance reporting.';


-- =============================================================================
-- DIMENSION: dim_alert_type
-- Classification taxonomy for thermal and operational alert events.
-- =============================================================================

CREATE TABLE dim_alert_type (
    alert_type_key      SERIAL          PRIMARY KEY,
    alert_code          VARCHAR(20)     NOT NULL UNIQUE,  -- 'THERM-CRIT', 'THERM-WARN', 'POWER-SURGE', etc.
    alert_category      VARCHAR(50)     NOT NULL,         -- 'Thermal', 'Power', 'Connectivity', 'Compliance'
    alert_name          VARCHAR(100)    NOT NULL,
    severity            VARCHAR(20)     NOT NULL,         -- 'Critical', 'High', 'Medium', 'Low'
    auto_shutoff        BOOLEAN         NOT NULL DEFAULT FALSE,  -- triggers device shutoff
    notifies_regional   BOOLEAN         NOT NULL DEFAULT FALSE,  -- triggers Teams alert to Regional Manager
    sla_response_mins   SMALLINT        NOT NULL          -- expected response window in minutes
);

COMMENT ON TABLE dim_alert_type IS
    'Alert taxonomy. severity and notifies_regional drive Power Automate bridge logic for Teams notifications.';


-- =============================================================================
-- FACT: fact_device_telemetry
-- Core event table. One row per telemetry reading from a deployed device.
-- ~2,000 rows generated by Python simulator.
-- =============================================================================

CREATE TABLE fact_device_telemetry (
    telemetry_key           BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES dim_date(date_key),
    device_key              INT             NOT NULL REFERENCES dim_device(device_key),
    store_key               INT             NOT NULL REFERENCES dim_store(store_key),
    alert_type_key          INT             REFERENCES dim_alert_type(alert_type_key),  -- NULL if no alert

    -- Timestamps
    event_timestamp         TIMESTAMP       NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- Thermal metrics
    temperature_celsius     NUMERIC(5,2)    NOT NULL,     -- surface temp reading
    max_temp_threshold      NUMERIC(5,2)    NOT NULL,     -- device safety ceiling (typically 230°C)
    temp_delta              NUMERIC(5,2)    NOT NULL,     -- diff from previous reading (LAG window fn source)
    is_thermal_spike        BOOLEAN         NOT NULL DEFAULT FALSE,  -- TRUE if temp > max_temp_threshold

    -- Operational metrics
    session_duration_secs   INT             NOT NULL,     -- length of use session
    power_draw_watts        NUMERIC(6,2)    NOT NULL,
    airflow_speed           SMALLINT        NOT NULL,     -- 1 (low) to 5 (high)

    -- Compliance / governance flags
    gdpr_compliant          BOOLEAN         NOT NULL DEFAULT TRUE,
    data_quality_flag       VARCHAR(20)     NOT NULL DEFAULT 'CLEAN',  -- 'CLEAN', 'NOISY', 'MISSING', 'SPIKE'
    is_anomaly              BOOLEAN         NOT NULL DEFAULT FALSE      -- set by Python anomaly detection script
);

COMMENT ON TABLE fact_device_telemetry IS
    'Core telemetry fact table. Grain = one reading per device session. '
    'date_key, device_key, store_key support all Tableau joins. '
    'alert_type_key is nullable — only populated when an alert condition is detected.';


-- =============================================================================
-- INDEXES
-- Supports Tableau query performance on high-cardinality filter columns.
-- =============================================================================

CREATE INDEX idx_telemetry_date        ON fact_device_telemetry(date_key);
CREATE INDEX idx_telemetry_device      ON fact_device_telemetry(device_key);
CREATE INDEX idx_telemetry_store       ON fact_device_telemetry(store_key);
CREATE INDEX idx_telemetry_spike       ON fact_device_telemetry(is_thermal_spike);
CREATE INDEX idx_telemetry_anomaly     ON fact_device_telemetry(is_anomaly);
CREATE INDEX idx_telemetry_timestamp   ON fact_device_telemetry(event_timestamp);


-- =============================================================================
-- VIEWS
-- Pre-built for Tableau and ad-hoc SQL analysis.
-- =============================================================================

-- High-risk store summary — stores with thermal spike rate above 10%
CREATE VIEW vw_high_risk_stores AS
SELECT
    s.store_id,
    s.store_name,
    s.city,
    s.country,
    s.region,
    COUNT(*)                                                        AS total_readings,
    SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)            AS spike_count,
    ROUND(
        SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)::NUMERIC
        / COUNT(*) * 100, 2
    )                                                               AS spike_rate_pct,
    AVG(f.temperature_celsius)                                      AS avg_temp,
    MAX(f.temperature_celsius)                                      AS max_temp_recorded
FROM fact_device_telemetry f
JOIN dim_store s ON f.store_key = s.store_key
GROUP BY s.store_key, s.store_id, s.store_name, s.city, s.country, s.region
HAVING
    ROUND(
        SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)::NUMERIC
        / COUNT(*) * 100, 2
    ) > 10
ORDER BY spike_rate_pct DESC;

COMMENT ON VIEW vw_high_risk_stores IS
    'Stores where thermal spike rate exceeds 10%. Primary source for Security Compliance map in Tableau.';


-- Device operational health summary
CREATE VIEW vw_device_health AS
SELECT
    d.device_id,
    d.model_version,
    d.firmware_version,
    s.store_name,
    s.region,
    COUNT(*)                                                        AS total_sessions,
    AVG(f.temperature_celsius)                                      AS avg_temp,
    AVG(f.session_duration_secs)                                    AS avg_session_secs,
    AVG(f.power_draw_watts)                                         AS avg_power_watts,
    SUM(CASE WHEN f.is_anomaly THEN 1 ELSE 0 END)                   AS anomaly_count,
    SUM(CASE WHEN f.data_quality_flag != 'CLEAN' THEN 1 ELSE 0 END) AS dirty_record_count
FROM fact_device_telemetry f
JOIN dim_device d  ON f.device_key = d.device_key
JOIN dim_store  s  ON f.store_key  = s.store_key
GROUP BY d.device_key, d.device_id, d.model_version, d.firmware_version,
         s.store_name, s.region;

COMMENT ON VIEW vw_device_health IS
    'Per-device operational summary. Feeds Operational Health dual-axis dashboard in Tableau.';

	SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'airlight'
ORDER BY table_type, table_name;

ALTER TABLE airlight.dim_date 
ALTER COLUMN fiscal_period TYPE VARCHAR(12);

ALTER TABLE airlight.fact_device_telemetry 
ALTER COLUMN temperature_celsius DROP NOT NULL;
# AirLight Pro IoT Governance System
# Data Dictionary
# Author: Alantz Innocent
# Description: Field-level documentation for all tables in the airlight schema.
#              Covers data types, business rules, valid values, and governance notes.

---

## Table of Contents

1. [fact_device_telemetry](#fact_device_telemetry)
2. [dim_store](#dim_store)
3. [dim_device](#dim_device)
4. [dim_date](#dim_date)
5. [dim_alert_type](#dim_alert_type)
6. [Views](#views)

---

## fact_device_telemetry

**Grain:** One row per device session telemetry reading.
**Row count:** ~2,000 (simulated)
**Date range:** January 2025 – March 2026

| Field | Type | Nullable | Description | Valid Values / Notes |
|---|---|---|---|---|
| `telemetry_key` | BIGSERIAL | No | Surrogate primary key | Auto-incremented |
| `date_key` | INT | No | FK to dim_date | Format: YYYYMMDD integer |
| `device_key` | INT | No | FK to dim_device | Must exist in dim_device |
| `store_key` | INT | No | FK to dim_store | Must exist in dim_store |
| `alert_type_key` | INT | Yes | FK to dim_alert_type | NULL if no alert triggered |
| `event_timestamp` | TIMESTAMP | No | Exact datetime of telemetry reading | UTC |
| `ingestion_timestamp` | TIMESTAMP | No | Datetime record was inserted into DB | Defaults to NOW() |
| `temperature_celsius` | NUMERIC(5,2) | Yes | Surface temperature of device in Celsius | Normal range: 150–229°C. Spike: >230°C. NULL = MISSING quality flag |
| `max_temp_threshold` | NUMERIC(5,2) | No | Device safety ceiling | Fixed at 230.0°C for AirLight Pro |
| `temp_delta` | NUMERIC(5,2) | No | Temperature difference from prior reading | Generated via Gaussian distribution (mean=0, σ=8.5) |
| `is_thermal_spike` | BOOLEAN | No | TRUE if temperature_celsius > max_temp_threshold | Drives alert_type_key assignment |
| `session_duration_secs` | INT | No | Length of device use session in seconds | Range: 120–1800 (2–30 minutes) |
| `power_draw_watts` | NUMERIC(6,2) | No | Power consumption during session | Range: 1200–1875W |
| `airflow_speed` | SMALLINT | No | Fan speed setting during session | 1 (low) to 5 (high) |
| `gdpr_compliant` | BOOLEAN | No | Whether record meets GDPR data handling standards | ~2% flagged FALSE to simulate governance issues |
| `data_quality_flag` | VARCHAR(20) | No | Quality classification of the record | CLEAN, NOISY, MISSING, SPIKE |
| `is_anomaly` | BOOLEAN | No | Statistical anomaly flag set by Python detection pipeline | Updated by anomaly_detection.py |

**Data Quality Flag Definitions:**

| Flag | Description | Frequency |
|---|---|---|
| `CLEAN` | Record passes all quality checks | ~88% |
| `MISSING` | temperature_celsius is NULL — sensor read failure | ~4% |
| `NOISY` | Temperature artificially distorted ±30°C | ~4% |
| `SPIKE` | Sudden unexplained temperature jump | ~4% |

---

## dim_store

**Grain:** One row per retail store location.
**Row count:** 10

| Field | Type | Nullable | Description | Valid Values / Notes |
|---|---|---|---|---|
| `store_key` | SERIAL | No | Surrogate primary key | Auto-incremented |
| `store_id` | VARCHAR(20) | No | Business key — human readable store code | Format: {COUNTRY}-{CITY}-{SEQ} e.g. US-NYC-001 |
| `store_name` | VARCHAR(100) | No | Display name of store | e.g. NYC Flagship |
| `city` | VARCHAR(100) | No | City where store is located | |
| `state_province` | VARCHAR(100) | Yes | State or province | NULL for non-US/CA locations |
| `country` | VARCHAR(100) | No | Country where store is located | |
| `region` | VARCHAR(50) | No | Geographic region grouping | North America, EMEA, APAC, LATAM |
| `store_tier` | VARCHAR(20) | No | Store classification | Flagship, Standard, Outlet |
| `store_open_date` | DATE | No | Date store opened | |
| `is_active` | BOOLEAN | No | Whether store is currently operational | Default TRUE |

**Regions:**

| Region | Countries |
|---|---|
| North America | USA |
| EMEA | UK, France, Germany |
| APAC | Japan, Australia |
| LATAM | Brazil |

---

## dim_device

**Grain:** One row per AirLight Pro unit deployed in a store.
**Row count:** 20 (2 devices per store)

| Field | Type | Nullable | Description | Valid Values / Notes |
|---|---|---|---|---|
| `device_key` | SERIAL | No | Surrogate primary key | Auto-incremented |
| `device_id` | VARCHAR(50) | No | Business key — unique device identifier | Format: ALP-2026-{5-digit seq} e.g. ALP-2026-00001 |
| `store_key` | INT | No | FK to dim_store | Each device assigned to exactly one store |
| `model_version` | VARCHAR(20) | No | Hardware model version | AirLight Pro v1, AirLight Pro v2 |
| `firmware_version` | VARCHAR(20) | No | Current firmware installed on device | FW-3.0.1, FW-3.1.2, FW-3.2.0 |
| `install_date` | DATE | No | Date device was installed in store | |
| `warranty_expiry` | DATE | No | Date device warranty expires | |
| `is_active` | BOOLEAN | No | Whether device is currently deployed | Default TRUE |
| `gdpr_masked` | BOOLEAN | No | Whether PII fields have been anonymized | TRUE = device data has been masked for GDPR compliance |

**Firmware Version Notes:**

| Version | Status | Notes |
|---|---|---|
| FW-3.0.1 | Legacy | Original release — higher spike rate observed |
| FW-3.1.2 | Current | Recommended version |
| FW-3.2.0 | Beta | Limited deployment — monitoring in progress |

---

## dim_date

**Grain:** One row per calendar date.
**Date range:** January 1, 2024 – December 31, 2026
**Row count:** 1,096

| Field | Type | Nullable | Description | Valid Values / Notes |
|---|---|---|---|---|
| `date_key` | INT | No | Surrogate primary key | Format: YYYYMMDD integer e.g. 20260101 |
| `full_date` | DATE | No | Calendar date | Unique |
| `day_of_week` | VARCHAR(10) | No | Day name | Monday through Sunday |
| `day_number` | SMALLINT | No | ISO day number | 1 (Monday) to 7 (Sunday) |
| `week_number` | SMALLINT | No | ISO week number | 1–53 |
| `month_number` | SMALLINT | No | Month number | 1–12 |
| `month_name` | VARCHAR(10) | No | Month name | January through December |
| `quarter` | SMALLINT | No | Calendar quarter | 1–4 |
| `year` | SMALLINT | No | Calendar year | 2024–2026 |
| `is_weekend` | BOOLEAN | No | TRUE for Saturday and Sunday | |
| `fiscal_period` | VARCHAR(12) | No | Fiscal period label | Format: FY{YEAR}-Q{QUARTER} e.g. FY2026-Q1 |

---

## dim_alert_type

**Grain:** One row per alert classification.
**Row count:** 5

| Field | Type | Nullable | Description | Valid Values / Notes |
|---|---|---|---|---|
| `alert_type_key` | SERIAL | No | Surrogate primary key | |
| `alert_code` | VARCHAR(20) | No | Business key — short alert identifier | THERM-CRIT, THERM-WARN, POWER-SURGE, CONN-LOST, COMPLIANCE |
| `alert_category` | VARCHAR(50) | No | Alert category grouping | Thermal, Power, Connectivity, Compliance |
| `alert_name` | VARCHAR(100) | No | Full descriptive name of alert | |
| `severity` | VARCHAR(20) | No | Alert severity level | Critical, High, Medium, Low |
| `auto_shutoff` | BOOLEAN | No | Whether alert triggers automatic device shutoff | TRUE for THERM-CRIT and POWER-SURGE |
| `notifies_regional` | BOOLEAN | No | Whether alert triggers Teams notification to Regional Manager | TRUE for THERM-CRIT and POWER-SURGE |
| `sla_response_mins` | SMALLINT | No | Expected response window in minutes | 5 (Critical) to 60 (Low) |

**Alert Code Reference:**

| Code | Category | Severity | Auto Shutoff | Notifies Regional | SLA |
|---|---|---|---|---|---|
| THERM-CRIT | Thermal | Critical | Yes | Yes | 5 min |
| THERM-WARN | Thermal | High | No | No | 15 min |
| POWER-SURGE | Power | High | Yes | Yes | 10 min |
| CONN-LOST | Connectivity | Medium | No | No | 30 min |
| COMPLIANCE | Compliance | Low | No | No | 60 min |

---

## Views

### vw_high_risk_stores

**Purpose:** Identifies stores with thermal spike rate exceeding 10%.
**Primary use:** Security Compliance Map in Tableau.

| Field | Description |
|---|---|
| `store_id` | Business key |
| `store_name` | Display name |
| `city` | City |
| `country` | Country |
| `region` | Region |
| `total_readings` | Total telemetry records for store |
| `spike_count` | Count of thermal spike records |
| `spike_rate_pct` | Percentage of readings that are thermal spikes |
| `avg_temp` | Average temperature across all sessions |
| `max_temp_recorded` | Highest temperature ever recorded at store |

### vw_device_health

**Purpose:** Per-device operational health summary.
**Primary use:** Operational Health dashboard in Tableau.

| Field | Description |
|---|---|
| `device_id` | Business key |
| `model_version` | Hardware model |
| `firmware_version` | Installed firmware |
| `store_name` | Store where device is deployed |
| `region` | Region |
| `total_sessions` | Total telemetry readings |
| `avg_temp` | Average session temperature |
| `avg_session_secs` | Average session duration |
| `avg_power_watts` | Average power consumption |
| `anomaly_count` | Total anomaly flags on device |
| `dirty_record_count` | Total non-CLEAN quality records |

---

*Last updated: April 2026*
*Schema version: 1.0*
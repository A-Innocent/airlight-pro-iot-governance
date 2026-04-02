-- =============================================================================
-- AirLight Pro IoT Governance System
-- Advanced SQL — Window Functions, CTEs, Analytical Queries
-- Author: Alantz
-- Description: Production-grade analytical queries demonstrating window
--              functions, CTEs, and advanced aggregations over the
--              AirLight Pro telemetry star schema.
-- =============================================================================

SET search_path TO airlight;


-- =============================================================================
-- 1. RANK — Top 5 highest spike rate stores globally
--    Uses RANK() with PARTITION BY region to show regional leaders
-- =============================================================================

WITH store_spike_rates AS (
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
        )                                                               AS spike_rate_pct
    FROM fact_device_telemetry f
    JOIN dim_store s ON f.store_key = s.store_key
    GROUP BY s.store_key, s.store_id, s.store_name, s.city, s.country, s.region
),
ranked_stores AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY region
            ORDER BY spike_rate_pct DESC
        )                                                               AS regional_rank,
        RANK() OVER (
            ORDER BY spike_rate_pct DESC
        )                                                               AS global_rank
    FROM store_spike_rates
)
SELECT
    global_rank,
    regional_rank,
    store_name,
    city,
    country,
    region,
    total_readings,
    spike_count,
    spike_rate_pct
FROM ranked_stores
ORDER BY global_rank
LIMIT 10;


-- =============================================================================
-- 2. LAG — Month-over-month temperature trend per store
--    Detects which stores are trending hotter vs prior month
-- =============================================================================

WITH monthly_temps AS (
    SELECT
        s.store_name,
        s.region,
        d.year,
        d.month_number,
        d.month_name,
        ROUND(AVG(f.temperature_celsius), 2)                            AS avg_temp
    FROM fact_device_telemetry f
    JOIN dim_store s ON f.store_key = s.store_key
    JOIN dim_date  d ON f.date_key  = d.date_key
    WHERE f.temperature_celsius IS NOT NULL
    GROUP BY s.store_name, s.region, d.year, d.month_number, d.month_name
),
mom_trend AS (
    SELECT
        store_name,
        region,
        year,
        month_number,
        month_name,
        avg_temp,
        LAG(avg_temp) OVER (
            PARTITION BY store_name
            ORDER BY year, month_number
        )                                                               AS prev_month_temp,
        ROUND(
            avg_temp - LAG(avg_temp) OVER (
                PARTITION BY store_name
                ORDER BY year, month_number
            ), 2
        )                                                               AS mom_temp_change
    FROM monthly_temps
)
SELECT
    store_name,
    region,
    year,
    month_name,
    avg_temp,
    prev_month_temp,
    mom_temp_change,
    CASE
        WHEN mom_temp_change > 2  THEN 'WARMING'
        WHEN mom_temp_change < -2 THEN 'COOLING'
        ELSE                           'STABLE'
    END                                                                 AS trend_status
FROM mom_trend
WHERE mom_temp_change IS NOT NULL
ORDER BY store_name, year, month_number;


-- =============================================================================
-- 3. LEAD — Predict next session temperature for anomaly early warning
--    Shows the NEXT reading's temp alongside current for each device
-- =============================================================================

WITH device_sessions AS (
    SELECT
        d.device_id,
        s.store_name,
        f.event_timestamp,
        f.temperature_celsius,
        f.is_thermal_spike,
        f.is_anomaly,
        LEAD(f.temperature_celsius) OVER (
            PARTITION BY f.device_key
            ORDER BY f.event_timestamp
        )                                                               AS next_session_temp,
        LEAD(f.is_thermal_spike) OVER (
            PARTITION BY f.device_key
            ORDER BY f.event_timestamp
        )                                                               AS next_session_spike
    FROM fact_device_telemetry f
    JOIN dim_device d ON f.device_key = d.device_key
    JOIN dim_store  s ON f.store_key  = s.store_key
    WHERE f.temperature_celsius IS NOT NULL
)
SELECT
    device_id,
    store_name,
    event_timestamp,
    temperature_celsius         AS current_temp,
    next_session_temp,
    ROUND(next_session_temp - temperature_celsius, 2)
                                AS temp_jump,
    next_session_spike          AS next_is_spike,
    CASE
        WHEN next_session_temp - temperature_celsius > 20
        THEN 'HIGH RISK — rapid temp escalation'
        WHEN next_session_spike = TRUE
        THEN 'SPIKE INCOMING'
        ELSE 'NORMAL'
    END                                                                 AS early_warning
FROM device_sessions
WHERE next_session_temp IS NOT NULL
ORDER BY temp_jump DESC NULLS LAST
LIMIT 50;


-- =============================================================================
-- 4. PARTITION BY + Running Total — Cumulative spike count per region
--    Shows how spikes accumulate over time by region
-- =============================================================================

WITH daily_spikes AS (
    SELECT
        s.region,
        d.full_date,
        d.year,
        d.month_number,
        SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)            AS daily_spikes
    FROM fact_device_telemetry f
    JOIN dim_store s ON f.store_key = s.store_key
    JOIN dim_date  d ON f.date_key  = d.date_key
    GROUP BY s.region, d.full_date, d.year, d.month_number
)
SELECT
    region,
    full_date,
    daily_spikes,
    SUM(daily_spikes) OVER (
        PARTITION BY region
        ORDER BY full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                                   AS cumulative_spikes,
    ROUND(AVG(daily_spikes) OVER (
        PARTITION BY region
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                                               AS rolling_7day_avg
FROM daily_spikes
ORDER BY region, full_date;


-- =============================================================================
-- 5. CTE + NTILE — Device performance quartile bucketing
--    Segments devices into performance tiers for maintenance prioritization
-- =============================================================================

WITH device_metrics AS (
    SELECT
        d.device_id,
        d.model_version,
        d.firmware_version,
        s.store_name,
        s.region,
        COUNT(*)                                                        AS total_sessions,
        ROUND(AVG(f.temperature_celsius), 2)                            AS avg_temp,
        SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)            AS total_spikes,
        SUM(CASE WHEN f.is_anomaly THEN 1 ELSE 0 END)                  AS total_anomalies,
        ROUND(
            SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)::NUMERIC
            / COUNT(*) * 100, 2
        )                                                               AS spike_rate_pct
    FROM fact_device_telemetry f
    JOIN dim_device d ON f.device_key = d.device_key
    JOIN dim_store  s ON f.store_key  = s.store_key
    WHERE f.temperature_celsius IS NOT NULL
    GROUP BY d.device_key, d.device_id, d.model_version,
             d.firmware_version, s.store_name, s.region
),
quartile_buckets AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY spike_rate_pct DESC)                   AS risk_quartile
    FROM device_metrics
)
SELECT
    device_id,
    store_name,
    region,
    model_version,
    firmware_version,
    total_sessions,
    avg_temp,
    total_spikes,
    spike_rate_pct,
    risk_quartile,
    CASE risk_quartile
        WHEN 1 THEN 'CRITICAL — immediate inspection required'
        WHEN 2 THEN 'HIGH — schedule maintenance within 7 days'
        WHEN 3 THEN 'MODERATE — monitor closely'
        WHEN 4 THEN 'HEALTHY — no action required'
    END                                                                 AS maintenance_priority
FROM quartile_buckets
ORDER BY risk_quartile, spike_rate_pct DESC;


-- =============================================================================
-- 6. DENSE_RANK + CTE — Firmware version performance comparison
--    Which firmware versions have the worst thermal compliance?
-- =============================================================================

WITH firmware_performance AS (
    SELECT
        d.firmware_version,
        COUNT(DISTINCT d.device_id)                                     AS device_count,
        COUNT(*)                                                        AS total_readings,
        ROUND(AVG(f.temperature_celsius), 2)                            AS avg_temp,
        SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)            AS total_spikes,
        ROUND(
            SUM(CASE WHEN f.is_thermal_spike THEN 1 ELSE 0 END)::NUMERIC
            / COUNT(*) * 100, 2
        )                                                               AS spike_rate_pct,
        ROUND(AVG(f.power_draw_watts), 2)                               AS avg_power_watts
    FROM fact_device_telemetry f
    JOIN dim_device d ON f.device_key = d.device_key
    WHERE f.temperature_celsius IS NOT NULL
    GROUP BY d.firmware_version
)
SELECT
    DENSE_RANK() OVER (ORDER BY spike_rate_pct DESC)                    AS compliance_rank,
    firmware_version,
    device_count,
    total_readings,
    avg_temp,
    total_spikes,
    spike_rate_pct,
    avg_power_watts,
    CASE
        WHEN spike_rate_pct > 10 THEN 'FAILED — force update required'
        WHEN spike_rate_pct > 7  THEN 'WARNING — update recommended'
        ELSE                          'COMPLIANT'
    END                                                                 AS compliance_status
FROM firmware_performance
ORDER BY compliance_rank;
# =============================================================================
# AirLight Pro IoT Governance System
# Anomaly Detection Pipeline
# Author: Alantz
# Description: Reads telemetry data from PostgreSQL, applies statistical
#              anomaly detection (Z-score + IQR methods) to temperature,
#              power draw, and session duration. Flags anomalies and writes
#              results back to fact_device_telemetry.
#              Also exports a clean anomaly report CSV for Tableau.
# =============================================================================

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

# =============================================================================
# DB CONNECTION
# =============================================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "Innocent#8389",   # <-- update if different
    "options":  "-c search_path=airlight"
}

# =============================================================================
# ANOMALY DETECTION METHODS
# =============================================================================

def zscore_anomaly(series, threshold=2.5):
    """
    Z-score method: flags values more than `threshold` standard deviations
    from the mean. Good for normally distributed data like temperature.
    Returns a boolean Series — True = anomaly.
    """
    mean   = series.mean()
    std    = series.std()
    if std == 0:
        return pd.Series([False] * len(series), index=series.index)
    zscores = (series - mean).abs() / std
    return zscores > threshold


def iqr_anomaly(series, multiplier=1.5):
    """
    IQR method: flags values outside (Q1 - 1.5*IQR) to (Q3 + 1.5*IQR).
    More robust than Z-score for skewed distributions like power draw.
    Returns a boolean Series — True = anomaly.
    """
    Q1  = series.quantile(0.25)
    Q3  = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - (multiplier * IQR)
    upper = Q3 + (multiplier * IQR)
    return (series < lower) | (series > upper)


def composite_anomaly(df):
    """
    Composite anomaly flag: a record is flagged if it triggers anomaly
    detection on ANY of the three key metrics:
      - temperature_celsius  (Z-score)
      - power_draw_watts     (IQR)
      - session_duration_secs (IQR)

    Also auto-flags records with data_quality_flag != 'CLEAN'.
    Returns the dataframe with new anomaly columns added.
    """
    clean = df[df["temperature_celsius"].notna()].copy()

    # Z-score on temperature
    clean["anomaly_temp"]    = zscore_anomaly(clean["temperature_celsius"], threshold=2.5)

    # IQR on power draw
    clean["anomaly_power"]   = iqr_anomaly(clean["power_draw_watts"], multiplier=1.5)

    # IQR on session duration
    clean["anomaly_session"] = iqr_anomaly(clean["session_duration_secs"], multiplier=1.5)

    # Data quality flag — any non-CLEAN record is suspicious
    clean["anomaly_quality"] = clean["data_quality_flag"] != "CLEAN"

    # Composite: flag if ANY method triggers
    clean["is_anomaly_detected"] = (
        clean["anomaly_temp"]    |
        clean["anomaly_power"]   |
        clean["anomaly_session"] |
        clean["anomaly_quality"]
    )

    # Anomaly reason string for reporting
    def build_reason(row):
        reasons = []
        if row["anomaly_temp"]:    reasons.append("TEMP_ZSCORE")
        if row["anomaly_power"]:   reasons.append("POWER_IQR")
        if row["anomaly_session"]: reasons.append("SESSION_IQR")
        if row["anomaly_quality"]: reasons.append(f"DATA_QUALITY:{row['data_quality_flag']}")
        return " | ".join(reasons) if reasons else "NONE"

    clean["anomaly_reason"] = clean.apply(build_reason, axis=1)

    return clean


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    # ------------------------------------------------------------------
    # 1. Load telemetry from DB
    # ------------------------------------------------------------------
    print("Loading telemetry data...")
    query = """
        SELECT
            f.telemetry_key,
            f.temperature_celsius,
            f.power_draw_watts,
            f.session_duration_secs,
            f.data_quality_flag,
            f.is_thermal_spike,
            f.is_anomaly,
            s.store_name,
            s.region,
            d.device_id,
            dt.full_date,
            dt.month_name,
            dt.year
        FROM fact_device_telemetry f
        JOIN dim_store  s  ON f.store_key  = s.store_key
        JOIN dim_device d  ON f.device_key = d.device_key
        JOIN dim_date   dt ON f.date_key   = dt.date_key
    """
    df = pd.read_sql(query, conn)
    print(f"Loaded {len(df):,} records.")

    # ------------------------------------------------------------------
    # 2. Run anomaly detection
    # ------------------------------------------------------------------
    print("\nRunning anomaly detection...")
    df_analyzed = composite_anomaly(df)

    total          = len(df_analyzed)
    detected       = df_analyzed["is_anomaly_detected"].sum()
    temp_flags     = df_analyzed["anomaly_temp"].sum()
    power_flags    = df_analyzed["anomaly_power"].sum()
    session_flags  = df_analyzed["anomaly_session"].sum()
    quality_flags  = df_analyzed["anomaly_quality"].sum()

    print(f"\n--- Anomaly Detection Results ---")
    print(f"Total records analyzed : {total:,}")
    print(f"Anomalies detected     : {detected:,}  ({round(detected/total*100, 1)}%)")
    print(f"  Temp Z-score flags   : {temp_flags:,}")
    print(f"  Power IQR flags      : {power_flags:,}")
    print(f"  Session IQR flags    : {session_flags:,}")
    print(f"  Data quality flags   : {quality_flags:,}")

    # ------------------------------------------------------------------
    # 3. Write anomaly flags back to PostgreSQL
    # ------------------------------------------------------------------
    print("\nWriting anomaly flags back to database...")
    update_count = 0

    for _, row in df_analyzed.iterrows():
        cur.execute("""
            UPDATE fact_device_telemetry
            SET is_anomaly = %s
            WHERE telemetry_key = %s
        """, (bool(row["is_anomaly_detected"]), int(row["telemetry_key"])))
        update_count += 1

    conn.commit()
    print(f"Updated {update_count:,} records in fact_device_telemetry.")

    # ------------------------------------------------------------------
    # 4. Export anomaly report to CSV for Tableau
    # ------------------------------------------------------------------
    print("\nExporting anomaly report CSV...")

    report = df_analyzed[df_analyzed["is_anomaly_detected"] == True][[
        "telemetry_key", "store_name", "region", "device_id",
        "full_date", "month_name", "year",
        "temperature_celsius", "power_draw_watts", "session_duration_secs",
        "data_quality_flag", "is_thermal_spike",
        "anomaly_temp", "anomaly_power", "anomaly_session", "anomaly_quality",
        "anomaly_reason"
    ]].copy()

    report["full_date"] = report["full_date"].astype(str)
    output_path = "C:/temp/airlight_anomaly_report.csv"
    report.to_csv(output_path, index=False)
    print(f"Anomaly report saved to {output_path}")
    print(f"Total anomaly records in report: {len(report):,}")

    # ------------------------------------------------------------------
    # 5. Summary by region
    # ------------------------------------------------------------------
    print("\n--- Anomaly Rate by Region ---")
    region_summary = df_analyzed.groupby("region").agg(
        total        = ("telemetry_key", "count"),
        anomalies    = ("is_anomaly_detected", "sum")
    ).reset_index()
    region_summary["anomaly_rate_pct"] = round(
        region_summary["anomalies"] / region_summary["total"] * 100, 1
    )
    print(region_summary.to_string(index=False))

    # ------------------------------------------------------------------
    # 6. Top 5 most anomalous devices
    # ------------------------------------------------------------------
    print("\n--- Top 5 Most Anomalous Devices ---")
    device_summary = df_analyzed.groupby(["device_id", "store_name"]).agg(
        total     = ("telemetry_key", "count"),
        anomalies = ("is_anomaly_detected", "sum")
    ).reset_index()
    device_summary["anomaly_rate_pct"] = round(
        device_summary["anomalies"] / device_summary["total"] * 100, 1
    )
    top5 = device_summary.nlargest(5, "anomaly_rate_pct")
    print(top5.to_string(index=False))

    cur.close()
    conn.close()
    print("\nAnomaly detection pipeline complete.")


if __name__ == "__main__":
    main()
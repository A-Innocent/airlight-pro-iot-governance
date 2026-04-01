# =============================================================================
# AirLight Pro IoT Governance System
# Data Simulator — generates 2,000 rows of realistic messy telemetry
# Author: Alantz
# Description: Simulates IoT telemetry from L'Oréal AirLight Pro infrared
#              hair dryer units deployed across global retail stores.
#              Inserts directly into PostgreSQL star schema.
#              Includes thermal spikes, dirty records, and anomalies.
# =============================================================================

import random
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)

# =============================================================================
# DB CONNECTION — update password if different
# =============================================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "Innocent#8389",   # <-- change if your password is different
    "options":  "-c search_path=airlight"
}

# =============================================================================
# REFERENCE DATA — mirrors what we'll seed into dimension tables
# =============================================================================

STORES = [
    {"store_key": 1,  "store_id": "US-NYC-001", "store_name": "NYC Flagship",        "city": "New York",    "country": "USA",     "region": "North America"},
    {"store_key": 2,  "store_id": "US-LAX-002", "store_name": "LA Beverly Hills",    "city": "Los Angeles", "country": "USA",     "region": "North America"},
    {"store_key": 3,  "store_id": "US-MIA-003", "store_name": "Miami Design District","city": "Miami",      "country": "USA",     "region": "North America"},
    {"store_key": 4,  "store_id": "US-CHI-004", "store_name": "Chicago Magnificent", "city": "Chicago",     "country": "USA",     "region": "North America"},
    {"store_key": 5,  "store_id": "UK-LON-001", "store_name": "London Oxford Street","city": "London",      "country": "UK",      "region": "EMEA"},
    {"store_key": 6,  "store_id": "FR-PAR-001", "store_name": "Paris Champs-Élysées","city": "Paris",       "country": "France",  "region": "EMEA"},
    {"store_key": 7,  "store_id": "DE-BER-001", "store_name": "Berlin Mitte",        "city": "Berlin",      "country": "Germany", "region": "EMEA"},
    {"store_key": 8,  "store_id": "JP-TKY-001", "store_name": "Tokyo Shibuya",       "city": "Tokyo",       "country": "Japan",   "region": "APAC"},
    {"store_key": 9,  "store_id": "AU-SYD-001", "store_name": "Sydney CBD",          "city": "Sydney",      "country": "Australia","region": "APAC"},
    {"store_key": 10, "store_id": "BR-SAO-001", "store_name": "São Paulo Jardins",   "city": "São Paulo",   "country": "Brazil",  "region": "LATAM"},
]

DEVICES = [
    {"device_key": i+1, "device_id": f"ALP-2026-{str(i+1).zfill(5)}",
     "store_key": STORES[i % len(STORES)]["store_key"],
     "model_version": random.choice(["AirLight Pro v1", "AirLight Pro v2"]),
     "firmware_version": random.choice(["FW-3.0.1", "FW-3.1.2", "FW-3.2.0"])}
    for i in range(20)
]

ALERT_TYPES = [
    {"alert_type_key": 1, "alert_code": "THERM-CRIT",   "severity": "Critical", "notifies_regional": True,  "auto_shutoff": True},
    {"alert_type_key": 2, "alert_code": "THERM-WARN",   "severity": "High",     "notifies_regional": False, "auto_shutoff": False},
    {"alert_type_key": 3, "alert_code": "POWER-SURGE",  "severity": "High",     "notifies_regional": True,  "auto_shutoff": True},
    {"alert_type_key": 4, "alert_code": "CONN-LOST",    "severity": "Medium",   "notifies_regional": False, "auto_shutoff": False},
    {"alert_type_key": 5, "alert_code": "COMPLIANCE",   "severity": "Low",      "notifies_regional": False, "auto_shutoff": False},
]

MAX_TEMP_THRESHOLD = 230.0  # °C — AirLight Pro safety ceiling

# =============================================================================
# DATE KEY HELPER
# =============================================================================

def date_to_key(dt):
    return int(dt.strftime("%Y%m%d"))

# =============================================================================
# SINGLE ROW GENERATOR
# =============================================================================

def generate_row(row_index):
    device      = random.choice(DEVICES)
    store_key   = device["store_key"]

    # Random timestamp between Jan 1 2025 and Mar 31 2026
    start_date  = datetime(2025, 1, 1)
    end_date    = datetime(2026, 3, 31)
    event_ts    = start_date + timedelta(
        seconds=random.randint(0, int((end_date - start_date).total_seconds()))
    )
    date_key    = date_to_key(event_ts)

    # --- Thermal simulation ---
    # Most readings are normal (150–210°C), ~8% are thermal spikes
    is_spike = random.random() < 0.08
    if is_spike:
        temperature = round(random.uniform(231.0, 265.0), 2)  # above threshold
    else:
        temperature = round(random.uniform(150.0, 229.0), 2)

    temp_delta      = round(random.gauss(0, 8.5), 2)   # realistic ±delta
    is_thermal_spike = temperature > MAX_TEMP_THRESHOLD

    # --- Operational metrics ---
    session_secs    = random.randint(120, 1800)         # 2 min to 30 min
    power_watts     = round(random.uniform(1200.0, 1875.0), 2)
    airflow_speed   = random.randint(1, 5)

    # --- Alert assignment ---
    alert_type_key  = None
    if is_thermal_spike:
        alert_type_key = 1 if temperature > 245.0 else 2  # THERM-CRIT vs THERM-WARN
    elif random.random() < 0.03:
        alert_type_key = random.choice([3, 4, 5])         # occasional other alerts

    # --- Data quality injection (~12% dirty records) ---
    quality_roll = random.random()
    if quality_roll < 0.04:
        data_quality_flag = "MISSING"
        temperature       = None    # simulate missing sensor read
    elif quality_roll < 0.08:
        data_quality_flag = "NOISY"
        temperature       = round(temperature + random.uniform(-30, 30), 2) if temperature else None
    elif quality_roll < 0.12:
        data_quality_flag = "SPIKE"
    else:
        data_quality_flag = "CLEAN"

    # --- Anomaly flag (~5% of records, independent of spikes) ---
    is_anomaly = random.random() < 0.05

    # --- GDPR compliance (~2% non-compliant to simulate governance issues) ---
    gdpr_compliant = random.random() > 0.02

    return {
        "date_key":             date_key,
        "device_key":           device["device_key"],
        "store_key":            store_key,
        "alert_type_key":       alert_type_key,
        "event_timestamp":      event_ts,
        "ingestion_timestamp":  datetime.now(),
        "temperature_celsius":  temperature,
        "max_temp_threshold":   MAX_TEMP_THRESHOLD,
        "temp_delta":           temp_delta,
        "is_thermal_spike":     is_thermal_spike,
        "session_duration_secs":session_secs,
        "power_draw_watts":     power_watts,
        "airflow_speed":        airflow_speed,
        "gdpr_compliant":       gdpr_compliant,
        "data_quality_flag":    data_quality_flag,
        "is_anomaly":           is_anomaly,
    }

# =============================================================================
# DIMENSION SEEDERS
# Inserts reference data into dim_store, dim_device, dim_alert_type, dim_date
# =============================================================================

def seed_dimensions(cur):
    print("Seeding dim_store...")
    for s in STORES:
        cur.execute("""
            INSERT INTO dim_store (store_key, store_id, store_name, city, country, region,
                                   state_province, store_tier, store_open_date, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, NULL, 'Flagship', '2020-01-01', TRUE)
            ON CONFLICT (store_id) DO NOTHING;
        """, (s["store_key"], s["store_id"], s["store_name"], s["city"], s["country"], s["region"]))

    print("Seeding dim_device...")
    for d in DEVICES:
        cur.execute("""
            INSERT INTO dim_device (device_key, device_id, store_key, model_version,
                                    firmware_version, install_date, warranty_expiry,
                                    is_active, gdpr_masked)
            VALUES (%s, %s, %s, %s, %s, '2024-06-01', '2027-06-01', TRUE, FALSE)
            ON CONFLICT (device_id) DO NOTHING;
        """, (d["device_key"], d["device_id"], d["store_key"],
              d["model_version"], d["firmware_version"]))

    print("Seeding dim_alert_type...")
    alert_meta = [
        (1, "THERM-CRIT",  "Thermal",     "Critical thermal event — device exceeds 245°C", "Critical", True,  True,  5),
        (2, "THERM-WARN",  "Thermal",     "Thermal warning — device above safe threshold",  "High",     False, False, 15),
        (3, "POWER-SURGE", "Power",       "Power draw surge detected",                      "High",     True,  True,  10),
        (4, "CONN-LOST",   "Connectivity","Device lost network connectivity",                "Medium",   False, False, 30),
        (5, "COMPLIANCE",  "Compliance",  "GDPR or data governance flag raised",             "Low",      False, False, 60),
    ]
    for a in alert_meta:
        cur.execute("""
            INSERT INTO dim_alert_type (alert_type_key, alert_code, alert_category, alert_name,
                                        severity, auto_shutoff, notifies_regional, sla_response_mins)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_code) DO NOTHING;
        """, a)

    print("Seeding dim_date (2024-01-01 to 2026-12-31)...")
    start = datetime(2024, 1, 1)
    end   = datetime(2026, 12, 31)
    current = start
    while current <= end:
        date_key     = date_to_key(current)
        day_name     = current.strftime("%A")
        day_num      = current.isoweekday()
        week_num     = current.isocalendar()[1]
        month_num    = current.month
        month_name   = current.strftime("%B")
        quarter      = (month_num - 1) // 3 + 1
        year         = current.year
        is_weekend   = day_num in (6, 7)
        fiscal       = f"FY{year}-Q{quarter}"
        cur.execute("""
            INSERT INTO dim_date (date_key, full_date, day_of_week, day_number, week_number,
                                  month_number, month_name, quarter, year, is_weekend, fiscal_period)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_date) DO NOTHING;
        """, (date_key, current.date(), day_name, day_num, week_num,
              month_num, month_name, quarter, year, is_weekend, fiscal))
        current += timedelta(days=1)
    print("dim_date seeded.")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    try:
        # Seed dimensions first
        seed_dimensions(cur)
        conn.commit()
        print("Dimensions committed.\n")

        # Generate and insert 2,000 telemetry rows
        print("Generating 2,000 telemetry rows...")
        rows = [generate_row(i) for i in range(2000)]
        df   = pd.DataFrame(rows)

        insert_sql = """
            INSERT INTO fact_device_telemetry (
                date_key, device_key, store_key, alert_type_key,
                event_timestamp, ingestion_timestamp,
                temperature_celsius, max_temp_threshold, temp_delta, is_thermal_spike,
                session_duration_secs, power_draw_watts, airflow_speed,
                gdpr_compliant, data_quality_flag, is_anomaly
            ) VALUES (
                %(date_key)s, %(device_key)s, %(store_key)s, %(alert_type_key)s,
                %(event_timestamp)s, %(ingestion_timestamp)s,
                %(temperature_celsius)s, %(max_temp_threshold)s, %(temp_delta)s, %(is_thermal_spike)s,
                %(session_duration_secs)s, %(power_draw_watts)s, %(airflow_speed)s,
                %(gdpr_compliant)s, %(data_quality_flag)s, %(is_anomaly)s
            );
        """

        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            cur.executemany(insert_sql, batch)
            print(f"  Inserted rows {i+1}–{min(i+batch_size, len(rows))}...")

        conn.commit()
        print("\nAll 2,000 rows committed.")

        # Quick summary
        cur.execute("SELECT COUNT(*) FROM fact_device_telemetry;")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fact_device_telemetry WHERE is_thermal_spike = TRUE;")
        spikes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fact_device_telemetry WHERE is_anomaly = TRUE;")
        anomalies = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fact_device_telemetry WHERE data_quality_flag != 'CLEAN';")
        dirty = cur.fetchone()[0]

        print(f"\n--- Summary ---")
        print(f"Total rows:      {total}")
        print(f"Thermal spikes:  {spikes}  ({round(spikes/total*100,1)}%)")
        print(f"Anomalies:       {anomalies}  ({round(anomalies/total*100,1)}%)")
        print(f"Dirty records:   {dirty}  ({round(dirty/total*100,1)}%)")
        print("\nAirLight Pro database is live.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
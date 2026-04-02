# AirLight Pro IoT Governance System
## Deployment Guide

**Version:** 1.0
**Last Updated:** April 2026
**Author:** Alantz

---

## Prerequisites

Before deploying the AirLight Pro system, ensure the following are installed:

| Requirement | Version | Download |
|---|---|---|
| PostgreSQL | 16+ | https://www.postgresql.org/download/ |
| Python | 3.12+ | https://www.python.org/downloads/ |
| Tableau Desktop | 2025+ | https://www.tableau.com/products/desktop |
| Git | Latest | https://git-scm.com/downloads |
| pgAdmin | 4+ | Included with PostgreSQL installer |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/A-Innocent/airlight-pro-iot-governance.git
cd airlight-pro-iot-governance
```

---

## Step 2 — Install Python Dependencies

```bash
pip install psycopg2-binary faker pandas numpy
```

Verify installation:
```bash
python -c "import psycopg2, pandas, numpy, faker; print('All dependencies installed.')"
```

---

## Step 3 — PostgreSQL Setup

### 3a. Create the database (if needed)
Open pgAdmin or psql and run:
```sql
CREATE DATABASE postgres;  -- skip if already exists
```

### 3b. Run the schema DDL
In pgAdmin, open the Query Tool, connect to the `postgres` database, and execute:
```
sql/01_schema_ddl.sql
```

This creates:
- Schema: `airlight`
- Tables: `fact_device_telemetry`, `dim_store`, `dim_device`, `dim_date`, `dim_alert_type`
- Views: `vw_high_risk_stores`, `vw_device_health`
- Indexes: 6 performance indexes on fact table

### 3c. Apply schema patches
Run these two ALTER statements in pgAdmin to fix column constraints:
```sql
ALTER TABLE airlight.dim_date
ALTER COLUMN fiscal_period TYPE VARCHAR(12);

ALTER TABLE airlight.fact_device_telemetry
ALTER COLUMN temperature_celsius DROP NOT NULL;
```

---

## Step 4 — Run the Data Simulator

Open `python/simulator.py` and verify the DB connection config at the top:

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "YOUR_PASSWORD_HERE",
    "options":  "-c search_path=airlight"
}
```

Then run:
```bash
python python/simulator.py
```

Expected output:
```
Connecting to PostgreSQL...
Seeding dim_store...
Seeding dim_device...
Seeding dim_alert_type...
Seeding dim_date (2024-01-01 to 2026-12-31)...
dim_date seeded.
Dimensions committed.
Generating 2,000 telemetry rows...
  Inserted rows 1–100...
  ...
All 2,000 rows committed.
--- Summary ---
Total rows:      2000
Thermal spikes:  ~142  (~7.1%)
Anomalies:       ~102  (~5.1%)
Dirty records:   ~225  (~11.2%)
AirLight Pro database is live.
```

---

## Step 5 — Run the Anomaly Detection Pipeline

```bash
python python/anomaly_detection.py
```

This script:
- Reads all telemetry from PostgreSQL
- Applies Z-score detection on temperature (threshold: 2.5σ)
- Applies IQR detection on power draw and session duration
- Writes updated `is_anomaly` flags back to `fact_device_telemetry`
- Exports `C:/temp/airlight_anomaly_report.csv` for Tableau

Expected output:
```
Total records analyzed : 1,931
Anomalies detected     : 167  (8.6%)
Highest risk region    : APAC (9.8%)
```

---

## Step 6 — Export Data for Tableau

Run this query in pgAdmin and export to `C:/temp/airlight_telemetry.csv`:

```sql
COPY (
    SELECT f.*, s.store_name, s.city, s.country, s.region,
           d.device_id, d.model_version, d.firmware_version,
           dt.full_date, dt.month_name, dt.quarter, dt.year,
           a.alert_code, a.severity
    FROM airlight.fact_device_telemetry f
    JOIN airlight.dim_store s    ON f.store_key      = s.store_key
    JOIN airlight.dim_device d   ON f.device_key     = d.device_key
    JOIN airlight.dim_date dt    ON f.date_key        = dt.date_key
    LEFT JOIN airlight.dim_alert_type a ON f.alert_type_key = a.alert_type_key
) TO 'C:/temp/airlight_telemetry.csv' WITH CSV HEADER;
```

---

## Step 7 — Open Tableau Dashboard

1. Open Tableau Desktop
2. Connect → To a File → Text File
3. Navigate to `C:/temp/airlight_telemetry.csv`
4. Open `tableau/AirLight_Pro_Executive_Dashboard.twbx`

The dashboard contains three views:
- **Security Compliance Map** — global spike rate by country
- **Operational Health** — dual-axis temperature vs session duration by month
- **Store vs Global Benchmark** — LOD expression store comparison

---

## Step 8 — Run Advanced SQL Queries (Optional)

Open `sql/02_window_functions_cte.sql` in pgAdmin and run individual queries to explore:
- Store spike rate rankings by region
- Month-over-month temperature trends
- Device risk quartile bucketing
- Firmware compliance rankings

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `fiscal_period too long` | VARCHAR(7) too short | Run ALTER in Step 3c |
| `temperature_celsius NOT NULL violation` | NULL values in MISSING records | Run ALTER in Step 3c |
| `psycopg2 connection refused` | PostgreSQL not running | Start PostgreSQL service in Windows Services |
| `COPY permission denied` | PostgreSQL can't write to path | Create `C:/temp/` folder manually |
| Tableau can't find CSV | Wrong path | Confirm CSV exists at `C:/temp/airlight_telemetry.csv` |

---

## Environment Notes

- All development and testing performed on Windows 11
- PostgreSQL running on localhost:5432
- Python virtual environment recommended for dependency isolation
- Tableau Desktop Public does not support live PostgreSQL connection — use CSV export method (Step 6)

---

*For questions or issues, open a GitHub issue in this repository.*
# AirLight Pro IoT Governance System

> Full-stack BI and analytics platform for L'Oréal's AirLight Pro infrared hair dryer IoT deployment across global retail stores. Built to demonstrate end-to-end data engineering, analytical SQL, Python pipeline development, and executive dashboard design.

---

## System Architecture

```
IoT Devices (Simulated)
        │
        ▼
Python Data Simulator
(2,000 rows, messy telemetry)
        │
        ▼
PostgreSQL Star Schema
(fact_device_telemetry + 4 dimensions)
        │
        ├──► Python Anomaly Detection Pipeline
        │    (Z-score + IQR → writes back to DB)
        │
        ├──► Advanced SQL Layer
        │    (Window functions, CTEs, analytical views)
        │
        └──► Tableau Executive Dashboards
             (Security Compliance Map, Operational Health,
              Store vs Global LOD Benchmark)
```

---

## Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 |
| Schema Design | SQL DDL — star schema |
| Data Simulation | Python 3.12, pandas, numpy, faker |
| Anomaly Detection | Python — Z-score, IQR statistical methods |
| Analytics | SQL window functions, CTEs, RANK, LAG, LEAD, NTILE |
| Dashboards | Tableau Desktop |
| Automation | Power Automate (thermal alert → Teams notification) |
| Version Control | Git / GitHub |

---

## Repository Structure

```
airlight-pro-iot-governance/
│
├── sql/
│   ├── 01_schema_ddl.sql           # Star schema DDL — all tables, views, indexes
│   └── 02_window_functions_cte.sql # Advanced analytical queries
│
├── python/
│   ├── simulator.py                # Data simulator — seeds all dimensions + 2,000 fact rows
│   └── anomaly_detection.py        # Statistical anomaly detection pipeline
│
├── tableau/
│   └── AirLight_Pro_Executive_Dashboard.twbx
│
├── docs/
│   ├── ERD.png                     # Entity-relationship diagram
│   ├── DATA_DICTIONARY.md          # Field-level documentation
│   └── DEPLOYMENT_GUIDE.md         # Step-by-step setup instructions
│
└── README.md
```

---

## Data Model

### Fact Table
**`fact_device_telemetry`** — grain: one row per device session reading
- 2,000 simulated rows spanning January 2025 – March 2026
- Thermal spikes: ~7.1% of readings exceed 230°C safety threshold
- Anomalies: 8.6% flagged by statistical detection pipeline
- Dirty records: ~11.2% contain MISSING, NOISY, or SPIKE quality flags

### Dimension Tables
| Table | Description |
|---|---|
| `dim_store` | 10 global retail locations across North America, EMEA, APAC, LATAM |
| `dim_device` | 20 AirLight Pro units, each assigned to a store |
| `dim_date` | Full date spine 2024–2026 with fiscal period, quarter, week number |
| `dim_alert_type` | 5 alert classifications with severity and SLA response windows |

### Views
| View | Purpose |
|---|---|
| `vw_high_risk_stores` | Stores with thermal spike rate > 10% |
| `vw_device_health` | Per-device operational health summary |

---

## Key Features

### SQL Layer
- Star schema with referential integrity and performance indexes
- Window functions: `RANK`, `DENSE_RANK`, `NTILE`, `LAG`, `LEAD`
- CTEs for readable, maintainable analytical query structure
- Month-over-month temperature trend classification (WARMING / COOLING / STABLE)
- Device risk quartile bucketing for maintenance prioritization
- Firmware compliance ranking by thermal spike rate

### Python Pipeline
- Simulates realistic IoT telemetry with controlled noise injection
- Z-score anomaly detection on temperature (threshold: 2.5σ)
- IQR anomaly detection on power draw and session duration
- Composite flagging — record flagged if any method triggers
- Writes anomaly flags back to PostgreSQL
- Exports anomaly report CSV for Tableau ingestion

### Tableau Dashboards
- **Security Compliance Map** — global choropleth of thermal spike rate by country
- **Operational Health** — dual-axis chart: avg temperature (bars) vs session duration (line) by month
- **Store vs Global Benchmark** — LOD expression comparing each store's avg temperature to global average, colored diverging red/blue

### Governance & Compliance
- `gdpr_compliant` flag on every telemetry record
- `gdpr_masked` flag on device registry
- `data_quality_flag` field tracks CLEAN / NOISY / MISSING / SPIKE records
- Power Automate bridge triggers Teams alert to Regional Manager on THERM-CRIT events

---

## Setup & Deployment

See [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) for full instructions.

**Quick start:**
```bash
# 1. Clone the repo
git clone https://github.com/A-Innocent/airlight-pro-iot-governance.git

# 2. Install Python dependencies
pip install psycopg2-binary faker pandas numpy

# 3. Create the schema in PostgreSQL
psql -U postgres -d postgres -f sql/01_schema_ddl.sql

# 4. Run the simulator to seed all data
python python/AirTight_Simulatorr.py

# 5. Run anomaly detection
python python/anomaly_detection.py

# 6. Open Tableau and connect to airlight_telemetry.csv or PostgreSQL
```

---

## Anomaly Detection Results

| Metric | Value |
|---|---|
| Total records analyzed | 1,931 |
| Anomalies detected | 167 (8.6%) |
| Temperature Z-score flags | 15 |
| Data quality flags | 156 |
| Highest risk region | APAC (9.8%) |
| Most anomalous device | ALP-2026-00009 — Sydney CBD (13.2%) |

---

## Business Context

This system is designed around a fictional L'Oréal product — the AirLight Pro 2026 infrared hair dryer — deployed across 10 global flagship retail locations. The governance platform monitors thermal safety compliance, device operational health, and data quality across the IoT fleet.

**Key business questions this system answers:**
- Which stores have the highest thermal spike rates and require immediate attention?
- Which devices are trending toward failure based on month-over-month temperature escalation?
- How does each store's thermal performance compare to the global fleet average?
- Which firmware versions are out of compliance with safety thresholds?
- Where are data quality issues concentrated in the telemetry pipeline?

---

## Author

**Alantz Innocent**
B.S. Computer Science — Western Governors University
Georgia Tech OMSCS — ML Track, Fall 2026
Certifications: Power BI Data Analyst, DP-600, CompTIA Data+, AZ-900, ITIL 4, Linux Essentials

---

*Built as a portfolio demonstration of full-stack Tablaeu development capabilities.*

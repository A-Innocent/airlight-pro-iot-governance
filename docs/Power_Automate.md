# AirLight Pro IoT Governance System
## Power Automate Bridge — Architecture & Flow Documentation

**Version:** 1.0
**Last Updated:** April 2026
**Author:** Alantz

---

## Overview

The Power Automate bridge is the automation layer of the AirLight Pro governance system. It monitors the PostgreSQL telemetry database for critical thermal events and routes real-time Microsoft Teams alerts to the responsible Regional Manager within the SLA response window.

**Trigger condition:** Any `THERM-CRIT` alert — device temperature exceeds 245°C
**SLA:** Regional Manager notified within 5 minutes of event detection
**Auto-action:** Device shutoff flag set automatically on THERM-CRIT and POWER-SURGE events

---

## Flow Architecture

```
Scheduled Trigger (every 15 min)
        │
        ▼
SQL Query Action
(SELECT THERM-CRIT events from fact_device_telemetry)
        │
        ▼
Condition: Any results returned?
        │
    YES │                    NO │
        ▼                       ▼
Apply to Each Loop          Terminate (no action)
(one iteration per alert)
        │
        ▼
Switch Action
(route by region)
        │
    ┌───┼───┬───────┐
    ▼   ▼   ▼       ▼
  NAM EMEA APAC  LATAM
        │
        ▼
Post Adaptive Card to Teams
(Regional Manager channel)
        │
        ▼
Send Email Action
(backup email notification)
        │
        ▼
Update SharePoint Log
(audit trail of all alerts sent)
```

---

## Flow Steps — Detailed

### Step 1: Scheduled Trigger
- **Type:** Recurrence
- **Frequency:** Every 15 minutes
- **Purpose:** Polls the database for new THERM-CRIT events on a regular interval

### Step 2: SQL Query Action
- **Connector:** SQL Server (or PostgreSQL via custom connector)
- **Query:**
```sql
SELECT
    f.telemetry_key,
    f.event_timestamp,
    f.temperature_celsius,
    f.max_temp_threshold,
    d.device_id,
    d.firmware_version,
    s.store_name,
    s.city,
    s.country,
    s.region,
    a.alert_code,
    a.severity,
    a.sla_response_mins
FROM fact_device_telemetry f
JOIN dim_device     d ON f.device_key     = d.device_key
JOIN dim_store      s ON f.store_key      = s.store_key
JOIN dim_alert_type a ON f.alert_type_key = a.alert_type_key
WHERE
    a.alert_code = 'THERM-CRIT'
    AND a.notifies_regional = TRUE
    AND f.event_timestamp >= DATEADD(minute, -15, GETUTCDATE())
```

### Step 3: Condition Check
- **Expression:** `empty(body('Execute_SQL_Query')?['resultsets']['Table1'])` is false
- **If yes:** Proceed to Apply to Each loop
- **If no:** Terminate flow — no alerts to process

### Step 4: Apply to Each Loop
- **Input:** Results from SQL query
- **Action:** Iterates over each THERM-CRIT alert record

### Step 5: Switch — Route by Region
- **Expression:** `items('Apply_to_each')?['region']`
- **Cases:** North America, EMEA, APAC, LATAM
- **Output:** Selects the correct Regional Manager Teams channel and email

### Step 6: Post Adaptive Card to Teams
- **Connector:** Microsoft Teams
- **Action:** Post adaptive card in a chat or channel
- **Card content includes:**
  - Store name, city, country
  - Device ID and firmware version
  - Temperature reading vs safety threshold
  - Overage amount (°C above limit)
  - SLA response window
  - Regional Manager mention (@teams handle)
  - Link to Tableau executive dashboard
  - Auto-shutoff confirmation

### Step 7: Send Email (Backup Notification)
- **Connector:** Office 365 Outlook
- **To:** Regional Manager email address
- **Subject:** `[CRITICAL] Thermal Alert — {store_name} — {device_id}`
- **Body:** Same alert details as Teams card
- **Purpose:** Ensures notification delivery even if Teams is unavailable

### Step 8: Update SharePoint Audit Log
- **Connector:** SharePoint
- **Action:** Create item in `AirLight-Alert-Log` list
- **Fields logged:** telemetry_key, store, device, temperature, region, manager notified, timestamp, notification status
- **Purpose:** GDPR-compliant audit trail of all governance alerts

---

## Regional Manager Routing Table

| Region | Manager | Teams Handle | SLA |
|---|---|---|---|
| North America | Sarah Mitchell | @sarah.mitchell | 5 min |
| EMEA | Jean-Pierre Dubois | @jeanpierre.dubois | 5 min |
| APAC | Yuki Tanaka | @yuki.tanaka | 5 min |
| LATAM | Carlos Mendez | @carlos.mendez | 5 min |

---

## Alert Severity & Actions

| Alert Code | Severity | Teams Notification | Email | Auto Shutoff | SLA |
|---|---|---|---|---|---|
| THERM-CRIT | Critical | Yes | Yes | Yes | 5 min |
| THERM-WARN | High | No | No | No | 15 min |
| POWER-SURGE | High | Yes | Yes | Yes | 10 min |
| CONN-LOST | Medium | No | No | No | 30 min |
| COMPLIANCE | Low | No | No | No | 60 min |

---

## Local Simulation

The file `python/power_automate_bridge.py` replicates this flow logic locally for testing and demonstration:

```bash
python python/power_automate_bridge.py
```

The script:
- Connects to PostgreSQL and queries for THERM-CRIT events
- Routes each alert to the correct Regional Manager
- Prints the simulated Teams notification to console
- Outputs the full Adaptive Card JSON payload

This allows full demonstration of the alert logic without requiring a live Power Automate environment.

---

## Production Deployment Notes

To deploy this flow in a production Microsoft 365 environment:

1. Import the flow template from Power Automate studio
2. Configure the PostgreSQL custom connector with production credentials
3. Update the Teams channel IDs for each regional manager
4. Update the SharePoint site URL for the audit log list
5. Set the recurrence trigger to 15-minute intervals
6. Enable flow monitoring and set up failure alerts

---

## GDPR Compliance Notes

- All alert notifications contain only operational data (temperature, device ID, store)
- No personally identifiable information (PII) is transmitted in Teams messages
- The SharePoint audit log is retained for 12 months per L'Oréal data retention policy
- Regional Managers are authorized data processors under the L'Oréal IoT governance framework

---

*For simulation code see: `python/power_automate_bridge.py`*
*For alert type definitions see: `docs/DATA_DICTIONARY.md#dim_alert_type`*
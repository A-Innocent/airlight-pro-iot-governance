# =============================================================================
# AirLight Pro IoT Governance System
# Power Automate Alert Bridge — Simulation Script
# Author: Alantz
# Description: Simulates the Power Automate bridge that monitors PostgreSQL
#              for THERM-CRIT events and triggers a Microsoft Teams
#              notification to the Regional Manager.
#
#              In production, this logic is implemented as a scheduled
#              Power Automate cloud flow. This script replicates the
#              detection and notification logic for local testing and
#              portfolio demonstration purposes.
# =============================================================================

import psycopg2
import pandas as pd
import json
from datetime import datetime, timedelta

# =============================================================================
# DB CONNECTION
# =============================================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "Innocent#8389",
    "options":  "-c search_path=airlight"
}

# =============================================================================
# REGIONAL MANAGER ROUTING TABLE
# Maps region to responsible manager — mirrors Power Automate's routing logic
# =============================================================================

REGIONAL_MANAGERS = {
    "North America": {
        "name":  "Sarah Mitchell",
        "email": "s.mitchell@loreal.com",
        "teams": "@sarah.mitchell"
    },
    "EMEA": {
        "name":  "Jean-Pierre Dubois",
        "email": "jp.dubois@loreal.com",
        "teams": "@jeanpierre.dubois"
    },
    "APAC": {
        "name":  "Yuki Tanaka",
        "email": "y.tanaka@loreal.com",
        "teams": "@yuki.tanaka"
    },
    "LATAM": {
        "name":  "Carlos Mendez",
        "email": "c.mendez@loreal.com",
        "teams": "@carlos.mendez"
    }
}

# =============================================================================
# ALERT DETECTION
# Queries for THERM-CRIT events in the last 24 hours
# In production this runs on a Power Automate scheduled trigger (every 15 min)
# =============================================================================

def fetch_critical_alerts(conn, hours_back=24):
    """
    Fetches all THERM-CRIT events within the lookback window.
    In Power Automate this is the SQL action step inside the scheduled flow.
    """
    query = """
        SELECT
            f.telemetry_key,
            f.event_timestamp,
            f.temperature_celsius,
            f.max_temp_threshold,
            f.temp_delta,
            f.session_duration_secs,
            d.device_id,
            d.model_version,
            d.firmware_version,
            s.store_id,
            s.store_name,
            s.city,
            s.country,
            s.region,
            a.alert_code,
            a.alert_name,
            a.severity,
            a.sla_response_mins
        FROM fact_device_telemetry f
        JOIN dim_device    d ON f.device_key      = d.device_key
        JOIN dim_store     s ON f.store_key        = s.store_key
        JOIN dim_alert_type a ON f.alert_type_key  = a.alert_type_key
        WHERE
            a.alert_code = 'THERM-CRIT'
            AND a.notifies_regional = TRUE
        ORDER BY f.temperature_celsius DESC
        LIMIT 20;
    """
    return pd.read_sql(query, conn)


# =============================================================================
# TEAMS MESSAGE BUILDER
# Replicates the Adaptive Card payload Power Automate sends to Teams
# =============================================================================

def build_teams_payload(alert_row, manager):
    """
    Builds the Microsoft Teams Adaptive Card JSON payload.
    In Power Automate this is the 'Post adaptive card to Teams channel' action.
    """
    temp        = alert_row["temperature_celsius"]
    threshold   = alert_row["max_temp_threshold"]
    overage     = round(float(temp) - float(threshold), 2) if temp and threshold else "N/A"
    timestamp   = str(alert_row["event_timestamp"])

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "🚨 CRITICAL THERMAL ALERT — AirLight Pro",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Attention"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Store",        "value": f"{alert_row['store_name']} ({alert_row['city']}, {alert_row['country']})"},
                                {"title": "Device ID",    "value": str(alert_row["device_id"])},
                                {"title": "Firmware",     "value": str(alert_row["firmware_version"])},
                                {"title": "Temperature",  "value": f"{temp}°C  (threshold: {threshold}°C)"},
                                {"title": "Overage",      "value": f"+{overage}°C above safety limit"},
                                {"title": "Alert Code",   "value": str(alert_row["alert_code"])},
                                {"title": "Severity",     "value": str(alert_row["severity"])},
                                {"title": "SLA",          "value": f"Response required within {alert_row['sla_response_mins']} minutes"},
                                {"title": "Timestamp",    "value": timestamp},
                                {"title": "Region",       "value": str(alert_row["region"])},
                                {"title": "Assigned To",  "value": f"{manager['name']} ({manager['teams']})"}
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": "Device has been automatically shut off. Immediate inspection required.",
                            "wrap": True,
                            "color": "Attention"
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Dashboard",
                            "url": "https://public.tableau.com/YOUR_DASHBOARD_URL"
                        }
                    ]
                }
            }
        ]
    }
    return payload


# =============================================================================
# ALERT PROCESSOR
# Loops through critical alerts and routes each to the correct Regional Manager
# =============================================================================

def process_alerts(alerts_df):
    """
    Processes each THERM-CRIT alert and simulates the Teams notification.
    In production this is a Power Automate 'Apply to each' loop action.
    """
    if alerts_df.empty:
        print("No THERM-CRIT alerts found in lookback window.")
        return

    print(f"Found {len(alerts_df)} THERM-CRIT alert(s) to process.\n")
    print("=" * 70)

    notifications_sent = []

    for _, alert in alerts_df.iterrows():
        region  = alert["region"]
        manager = REGIONAL_MANAGERS.get(region, {
            "name": "Global Operations", "email": "ops@loreal.com", "teams": "@global.ops"
        })

        payload = build_teams_payload(alert, manager)

        # Simulate the Teams POST (in production this hits the Teams webhook URL)
        print(f"ALERT TRIGGERED")
        print(f"  Store:       {alert['store_name']} — {alert['city']}, {alert['country']}")
        print(f"  Device:      {alert['device_id']} ({alert['firmware_version']})")
        print(f"  Temperature: {alert['temperature_celsius']}°C  (limit: {alert['max_temp_threshold']}°C)")
        print(f"  Region:      {region}")
        print(f"  Notifying:   {manager['name']} via Teams ({manager['teams']})")
        print(f"  SLA:         {alert['sla_response_mins']} minute response window")
        print(f"  Status:      [SIMULATED] Teams notification sent ✓")
        print("-" * 70)

        notifications_sent.append({
            "telemetry_key": alert["telemetry_key"],
            "store":         alert["store_name"],
            "device":        alert["device_id"],
            "temperature":   alert["temperature_celsius"],
            "region":        region,
            "manager":       manager["name"],
            "timestamp":     str(datetime.now())
        })

    print(f"\nSummary: {len(notifications_sent)} Teams notification(s) simulated.")
    print("\nSample Adaptive Card Payload (first alert):")
    first_payload = build_teams_payload(alerts_df.iloc[0],
        REGIONAL_MANAGERS.get(alerts_df.iloc[0]["region"], {}))
    print(json.dumps(first_payload["attachments"][0]["content"]["body"][1], indent=2))

    return notifications_sent


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("AirLight Pro — Power Automate Alert Bridge Simulation")
    print("=" * 70)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulating scheduled Power Automate flow trigger (every 15 min)\n")

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        print("Checking for THERM-CRIT events...")
        alerts = fetch_critical_alerts(conn, hours_back=24)
        process_alerts(alerts)

    finally:
        conn.close()

    print("\nPower Automate bridge simulation complete.")
    print("In production: this script is replaced by a Power Automate")
    print("cloud flow scheduled to run every 15 minutes.")


if __name__ == "__main__":
    main()
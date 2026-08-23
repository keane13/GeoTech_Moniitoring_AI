import os
import streamlit as st

# ---------------------------------------------------------------------------
# Dual-mode session: Snowflake SiS (production) vs local dev
# ---------------------------------------------------------------------------
session = None
connection_error = None

try:
    # 1. Try running inside Streamlit in Snowflake — use the injected session
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
except Exception as e_sis:
    # 2. Running locally (or SiS failed) — try loading credentials
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")
        env_example_path = os.path.join(base_dir, ".env.example")
        
        target_env = env_path if os.path.exists(env_path) else (env_example_path if os.path.exists(env_example_path) else None)
        if target_env:
            with open(target_env, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
    except Exception:
        pass  # ignore file parsing errors

    try:
        account = os.environ.get("SNOWFLAKE_ACCOUNT")
        if not account:
            raise ValueError(f"SNOWFLAKE_ACCOUNT not found in environment variables. SiS Error was: {e_sis}")

        from snowflake.snowpark import Session
        session = Session.builder.configs({
            "account":   account,
            "user":      os.environ.get("SNOWFLAKE_USER"),
            "password":  os.environ.get("SNOWFLAKE_PASSWORD"),
            "role":      os.environ.get("SNOWFLAKE_ROLE", ""),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
            "database":  os.environ.get("SNOWFLAKE_DATABASE", "GEOTECH"),
            "schema":    os.environ.get("SNOWFLAKE_SCHEMA", "CORE"),
        }).create()
    except Exception as e_local:
        connection_error = str(e_local)


import pandas as pd

def get_facilities():
    try:
        return session.sql("SELECT * FROM GEOTECH.CORE.FACILITIES ORDER BY facility_id").to_pandas()
    except Exception:
        return pd.DataFrame(columns=["FACILITY_ID", "FACILITY_NAME", "REGION", "LATITUDE", "LONGITUDE", "RISK_LEVEL", "LAST_INSPECTION"])

def get_sensors():
    try:
        return session.sql("SELECT * FROM GEOTECH.CORE.SENSORS ORDER BY sensor_id").to_pandas()
    except Exception:
        return pd.DataFrame(columns=["SENSOR_ID", "FACILITY_ID", "ZONE", "SENSOR_TYPE", "INSTALLATION_DATE", "STATUS"])

def get_audit_cases():
    try:
        return session.sql("SELECT * FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY risk_score DESC").to_pandas()
    except Exception:
        return pd.DataFrame(columns=["CASE_ID", "SENSOR_ID", "DETECTED_PATTERN", "RISK_SCORE", "SEVERITY", "RECOMMENDED_ACTION", "FINAL_ACTION", "APPROVAL_STATUS", "DETECTED_TS"])

def get_escalations_30d():
    try:
        return session.sql("""
            SELECT * FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG
            WHERE escalation_ts >= DATEADD('day', -30, CURRENT_TIMESTAMP())
        """).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["ESCALATION_ID", "CASE_ID", "ESCALATION_LEVEL", "ESCALATION_TS", "RESOLVED"])

def get_sensor_readings(sensor_id):
    try:
        return session.sql(f"""
            SELECT reading_ts, reading_value, data_quality_flag
            FROM GEOTECH.CORE.SENSOR_READINGS
            WHERE sensor_id = '{sensor_id}' AND data_quality_flag = 'NORMAL'
            ORDER BY reading_ts
        """).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["READING_TS", "READING_VALUE", "DATA_QUALITY_FLAG"])

def get_zone_readings(facility_id, zone):
    try:
        return session.sql(f"""
            SELECT r.sensor_id, r.reading_ts, r.reading_value
            FROM GEOTECH.CORE.SENSOR_READINGS r
            JOIN GEOTECH.CORE.SENSORS s ON r.sensor_id = s.sensor_id
            WHERE s.facility_id = '{facility_id}' AND s.zone = '{zone}'
              AND r.data_quality_flag = 'NORMAL'
              AND r.reading_ts >= DATEADD('day', -90, CURRENT_DATE())
            ORDER BY r.reading_ts
        """).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["SENSOR_ID", "READING_TS", "READING_VALUE"])

def get_personnel():
    try:
        return session.sql("SELECT ENGINEER_ID, NAME, ROLE, FACILITY_ID FROM GEOTECH.CORE.PERSONNEL ORDER BY NAME").to_pandas()
    except Exception:
        return pd.DataFrame(columns=["ENGINEER_ID", "NAME", "ROLE", "FACILITY_ID"])

def get_detection_accuracy():
    try:
        return session.sql("""
            SELECT
              CASE 
                WHEN g.INJECTED_PATTERN != 'NONE' AND a.SENSOR_ID IS NOT NULL THEN 'TRUE_POSITIVE'
                WHEN g.INJECTED_PATTERN = 'NONE' AND a.SENSOR_ID IS NOT NULL THEN 'FALSE_POSITIVE'
                WHEN g.INJECTED_PATTERN != 'NONE' AND a.SENSOR_ID IS NULL THEN 'FALSE_NEGATIVE'
                ELSE 'TRUE_NEGATIVE' 
              END AS CONFUSION_CLASS,
              COUNT(DISTINCT g.SENSOR_ID) AS SENSOR_COUNT
            FROM GEOTECH.CORE.GROUND_TRUTH_LABELS g
            LEFT JOIN (SELECT DISTINCT SENSOR_ID FROM GEOTECH.CORE.GEOTECH_AUDIT) a ON g.SENSOR_ID = a.SENSOR_ID
            GROUP BY CONFUSION_CLASS
        """).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["CONFUSION_CLASS", "SENSOR_COUNT"])

def approve_and_dispatch(case_id, engineer_name, action, approved_by):
    session.sql(f"""
        UPDATE GEOTECH.CORE.GEOTECH_AUDIT
        SET FINAL_ACTION = '{action}',
            ASSIGNED_ENGINEER = '{engineer_name}',
            ACTION_TS = CURRENT_TIMESTAMP(),
            APPROVAL_STATUS = 'APPROVED',
            APPROVED_BY = '{approved_by}',
            APPROVED_TS = CURRENT_TIMESTAMP()
        WHERE CASE_ID = '{case_id}'
    """).collect()
    if action in ('SCHEDULE_INSPECTION', 'URGENT_INSPECTION'):
        facility_id = session.sql(f"SELECT FACILITY_ID FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE CASE_ID = '{case_id}'").collect()[0][0]
        session.sql(f"""
            INSERT INTO GEOTECH.CORE.INSPECTION_LOG (INSPECTION_ID, FACILITY_ID, INSPECTION_DATE, INSPECTOR_NAME, INSPECTION_TYPE, FINDINGS, FOLLOW_UP_REQUIRED)
            VALUES (
                'INS-' || TO_CHAR(CURRENT_TIMESTAMP(), 'YYYYMMDDHH24MISS'),
                '{facility_id}',
                CURRENT_DATE(),
                '{engineer_name}',
                'TRIGGERED',
                'Auto-dispatched from case {case_id} — {action}',
                TRUE
            )
        """).collect()

def reject_case(case_id, approved_by):
    session.sql(f"""
        UPDATE GEOTECH.CORE.GEOTECH_AUDIT
        SET APPROVAL_STATUS = 'REJECTED',
            APPROVED_BY = '{approved_by}',
            APPROVED_TS = CURRENT_TIMESTAMP(),
            FINAL_ACTION = 'REJECTED'
        WHERE CASE_ID = '{case_id}'
    """).collect()

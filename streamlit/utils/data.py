import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()


@st.cache_data(ttl=300)
def get_facilities():
    return session.sql("SELECT * FROM GEOTECH.CORE.FACILITIES ORDER BY facility_id").to_pandas()


@st.cache_data(ttl=300)
def get_sensors():
    return session.sql("SELECT * FROM GEOTECH.CORE.SENSORS ORDER BY sensor_id").to_pandas()


@st.cache_data(ttl=300)
def get_audit_cases():
    return session.sql("SELECT * FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY risk_score DESC").to_pandas()


@st.cache_data(ttl=300)
def get_escalations_30d():
    return session.sql("""
        SELECT * FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG
        WHERE escalation_ts >= DATEADD('day', -30, CURRENT_TIMESTAMP())
    """).to_pandas()


@st.cache_data(ttl=60)
def get_sensor_readings(sensor_id):
    return session.sql(f"""
        SELECT reading_ts, reading_value, data_quality_flag
        FROM GEOTECH.CORE.SENSOR_READINGS
        WHERE sensor_id = '{sensor_id}' AND data_quality_flag = 'NORMAL'
        ORDER BY reading_ts
    """).to_pandas()


@st.cache_data(ttl=60)
def get_zone_readings(facility_id, zone):
    return session.sql(f"""
        SELECT r.sensor_id, r.reading_ts, r.reading_value
        FROM GEOTECH.CORE.SENSOR_READINGS r
        JOIN GEOTECH.CORE.SENSORS s ON r.sensor_id = s.sensor_id
        WHERE s.facility_id = '{facility_id}' AND s.zone = '{zone}'
          AND r.data_quality_flag = 'NORMAL'
          AND r.reading_ts >= DATEADD('day', -90, CURRENT_DATE())
        ORDER BY r.reading_ts
    """).to_pandas()


@st.cache_data(ttl=300)
def get_personnel():
    return session.sql("SELECT ENGINEER_ID, NAME, ROLE, FACILITY_ID FROM GEOTECH.CORE.PERSONNEL ORDER BY NAME").to_pandas()


@st.cache_data(ttl=600)
def get_detection_accuracy():
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
    get_audit_cases.clear()


def reject_case(case_id, approved_by):
    session.sql(f"""
        UPDATE GEOTECH.CORE.GEOTECH_AUDIT
        SET APPROVAL_STATUS = 'REJECTED',
            APPROVED_BY = '{approved_by}',
            APPROVED_TS = CURRENT_TIMESTAMP(),
            FINAL_ACTION = 'REJECTED'
        WHERE CASE_ID = '{case_id}'
    """).collect()
    get_audit_cases.clear()

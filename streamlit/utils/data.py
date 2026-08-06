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

# GeoTech Monitoring AI template-based chatbot with 55+ SQL query patterns
# Co-authored with CoCo
import streamlit as st
import pandas as pd
import time
import re

from utils.data import session


def _rerun():
    """Streamlit renamed experimental_rerun() to rerun() in 1.27. Snowflake's
    runtime may ship either, so dispatch to whichever exists."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.rerun()


# =============================================================================
# TEMPLATE ENGINE — pattern library covering all GEOTECH.CORE tables,
# organised by the skill each pattern belongs to
# =============================================================================

TEMPLATES = [
    # --- AGENTIC PIPELINE EXPLANATIONS (For Hackathon Judges) ---
    {
        "skill": "action",
        "keywords": ["what", "is", "action", "orchestrator"],
        "sql": "SELECT 'The Action Orchestrator reads recommended actions, branches deterministically based on severity, writes the final action + timestamp, and creates necessary log entries in INSPECTION_LOG or EMERGENCY_ESCALATION_LOG.' AS DEFINITION",
        "narration": "The Action Orchestrator is the final stage of our agentic pipeline. It handles deterministic routing of AI recommendations, ensuring critical and high-severity cases trigger proper downstream workflows like emergency escalations or urgent inspections."
    },
    {
        "skill": "drift",
        "keywords": ["how", "does", "drift", "scan", "work"],
        "sql": "SELECT 'Drift Scan analyzes historical sensor data using deterministic rules: baseline regression, rate-of-change spikes, threshold extrapolation, and cross-sensor correlation. It identifies anomalies and writes new rows to GEOTECH_AUDIT without LLM rationale.' AS DEFINITION",
        "narration": "Drift Scan is the first stage. It continuously monitors sensor telemetry for anomalous patterns (like sudden spikes, sustained trends, or threshold approaches) using deterministic statistical methods. Flagged cases are queued for synthesis."
    },
    {
        "skill": "risk",
        "keywords": ["what", "is", "risk", "synthesis"],
        "sql": "SELECT 'Risk Synthesis reads unresolved GEOTECH_AUDIT rows, joins context from FACILITIES and INSPECTION_LOG, and generates an LLM rationale and recommended action for the flagged sensor anomaly.' AS DEFINITION",
        "narration": "Risk Synthesis is the second stage. It takes the anomalies flagged by Drift Scan, gathers rich contextual data (like facility risk classification and past inspections), and uses a Large Language Model (Snowflake Cortex) to synthesize a human-readable risk rationale and recommend a mitigation action."
    },
    # --- RISK & SEVERITY ---
    {
        "keywords": ["top", "highest", "risk", "score"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, SEVERITY, PATTERN_TRIGGERED, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY RISK_SCORE DESC LIMIT 10",
        "narration": "Here are the top 10 cases by risk score."
    },
    {
        "keywords": ["critical", "cases"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, DAYS_TO_THRESHOLD, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE SEVERITY = 'CRITICAL' ORDER BY RISK_SCORE DESC",
        "narration": "All critical severity cases in the system."
    },
    {
        "keywords": ["high", "severity"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, DAYS_TO_THRESHOLD, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE SEVERITY = 'HIGH' ORDER BY RISK_SCORE DESC",
        "narration": "All high severity cases."
    },
    {
        "keywords": ["severity", "count"],
        "sql": "SELECT SEVERITY, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY SEVERITY ORDER BY CASE_COUNT DESC",
        "narration": "Distribution of cases by severity level."
    },
    {
        "keywords": ["severity", "distribution"],
        "sql": "SELECT SEVERITY, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY SEVERITY ORDER BY CASE_COUNT DESC",
        "narration": "Distribution of cases by severity level."
    },
    {
        "keywords": ["average", "risk", "score", "facility"],
        "sql": "SELECT f.FACILITY_NAME, ROUND(AVG(a.RISK_SCORE), 2) AS AVG_RISK_SCORE, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID GROUP BY f.FACILITY_NAME ORDER BY AVG_RISK_SCORE DESC",
        "narration": "Average risk score per facility."
    },
    {
        "keywords": ["average", "risk", "score"],
        "sql": "SELECT ROUND(AVG(RISK_SCORE), 2) AS AVG_RISK, ROUND(MAX(RISK_SCORE), 2) AS MAX_RISK, ROUND(MIN(RISK_SCORE), 2) AS MIN_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT",
        "narration": "Overall risk score statistics."
    },
    {
        "keywords": ["risk", "by", "zone"],
        "sql": "SELECT ZONE, ROUND(AVG(RISK_SCORE), 2) AS AVG_RISK, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY ZONE ORDER BY AVG_RISK DESC",
        "narration": "Risk scores broken down by zone."
    },
    {
        "keywords": ["risk", "trend", "time"],
        "sql": "SELECT DATE_TRUNC('day', DETECTED_TS) AS DETECTION_DATE, ROUND(AVG(RISK_SCORE), 2) AS AVG_RISK, COUNT(*) AS CASES FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY DETECTION_DATE ORDER BY DETECTION_DATE",
        "narration": "Risk score trend over time."
    },
    # --- FACILITIES ---
    {
        "keywords": ["all", "facilities"],
        "sql": "SELECT FACILITY_ID, FACILITY_NAME, LOCATION, DAM_TYPE, RISK_CLASSIFICATION, DAM_HEIGHT_M, STORAGE_CAPACITY_MM3, COMMISSIONED_DATE, STATUS FROM GEOTECH.CORE.FACILITIES ORDER BY FACILITY_NAME",
        "narration": "All registered facilities."
    },
    {
        "keywords": ["facility", "list"],
        "sql": "SELECT FACILITY_ID, FACILITY_NAME, LOCATION, DAM_TYPE, RISK_CLASSIFICATION, DAM_HEIGHT_M, STORAGE_CAPACITY_MM3, COMMISSIONED_DATE, STATUS FROM GEOTECH.CORE.FACILITIES ORDER BY FACILITY_NAME",
        "narration": "Complete facility listing."
    },
    {
        "keywords": ["extreme", "risk", "facility"],
        "sql": "SELECT FACILITY_ID, FACILITY_NAME, LOCATION, DAM_TYPE, DAM_HEIGHT_M, STORAGE_CAPACITY_MM3, COMMISSIONED_DATE, REGULATORY_BODY, STATUS FROM GEOTECH.CORE.FACILITIES WHERE RISK_CLASSIFICATION = 'EXTREME' ORDER BY DAM_HEIGHT_M DESC",
        "narration": "Facilities classified as EXTREME risk."
    },
    {
        "keywords": ["tailings", "dam"],
        "sql": "SELECT FACILITY_ID, FACILITY_NAME, DAM_TYPE, DAM_HEIGHT_M, STORAGE_CAPACITY_MM3, RISK_CLASSIFICATION, REGULATORY_BODY FROM GEOTECH.CORE.FACILITIES ORDER BY DAM_HEIGHT_M DESC",
        "narration": "All tailings dam facilities."
    },
    {
        "keywords": ["facility", "type", "count"],
        "sql": "SELECT DAM_TYPE, COUNT(*) AS FACILITY_COUNT, ROUND(AVG(DAM_HEIGHT_M),1) AS AVG_HEIGHT_M FROM GEOTECH.CORE.FACILITIES GROUP BY DAM_TYPE ORDER BY FACILITY_COUNT DESC",
        "narration": "Facilities grouped by type."
    },
    {
        "keywords": ["oldest", "facility"],
        "sql": "SELECT FACILITY_ID, FACILITY_NAME, DAM_TYPE, COMMISSIONED_DATE, DATEDIFF('year', COMMISSIONED_DATE, CURRENT_DATE()) AS AGE_YEARS, RISK_CLASSIFICATION FROM GEOTECH.CORE.FACILITIES ORDER BY COMMISSIONED_DATE ASC",
        "narration": "Oldest facilities by construction year."
    },
    {
        "keywords": ["dam", "safety", "review"],
        "sql": "SELECT f.FACILITY_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, MAX(i.INSPECTION_DATE) AS LAST_DSR_DATE, DATEDIFF('day', MAX(i.INSPECTION_DATE), CURRENT_DATE()) AS DAYS_SINCE_REVIEW FROM GEOTECH.CORE.FACILITIES f LEFT JOIN GEOTECH.CORE.INSPECTION_LOG i ON f.FACILITY_ID = i.FACILITY_ID AND i.INSPECTION_TYPE = 'ANNUAL_DSR' GROUP BY f.FACILITY_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION ORDER BY DAYS_SINCE_REVIEW DESC NULLS FIRST",
        "narration": "Facilities sorted by time since last dam safety review."
    },
    # --- SENSORS ---
    {
        "keywords": ["sensor", "count", "facility"],
        "sql": "SELECT f.FACILITY_NAME, COUNT(s.SENSOR_ID) AS SENSOR_COUNT FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID GROUP BY f.FACILITY_NAME ORDER BY SENSOR_COUNT DESC",
        "narration": "Sensor count per facility."
    },
    {
        "keywords": ["sensor", "type", "count"],
        "sql": "SELECT SENSOR_TYPE, COUNT(*) AS SENSOR_COUNT FROM GEOTECH.CORE.SENSORS GROUP BY SENSOR_TYPE ORDER BY SENSOR_COUNT DESC",
        "narration": "Sensors grouped by type."
    },
    {
        "keywords": ["sensor", "type", "distribution"],
        "sql": "SELECT SENSOR_TYPE, COUNT(*) AS SENSOR_COUNT FROM GEOTECH.CORE.SENSORS GROUP BY SENSOR_TYPE ORDER BY SENSOR_COUNT DESC",
        "narration": "Distribution of sensors by type."
    },
    {
        "keywords": ["piezometer"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'PIEZOMETER' ORDER BY s.SENSOR_ID",
        "narration": "All piezometer sensors with their thresholds."
    },
    {
        "keywords": ["inclinometer"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'INCLINOMETER' ORDER BY s.SENSOR_ID",
        "narration": "All inclinometer sensors."
    },
    {
        "keywords": ["extensometer"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'EXTENSOMETER' ORDER BY s.SENSOR_ID",
        "narration": "All extensometer sensors."
    },
    {
        "keywords": ["survey", "prism"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'SURVEY_PRISM' ORDER BY s.SENSOR_ID",
        "narration": "All survey prism sensors."
    },
    {
        "keywords": ["settlement", "cell"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'SETTLEMENT_CELL' ORDER BY s.SENSOR_ID",
        "narration": "All settlement plate sensors."
    },
    {
        "keywords": ["sensor", "zone"],
        "sql": "SELECT ZONE, COUNT(*) AS SENSOR_COUNT FROM GEOTECH.CORE.SENSORS GROUP BY ZONE ORDER BY SENSOR_COUNT DESC",
        "narration": "Sensors grouped by zone."
    },
    {
        "keywords": ["calibration", "overdue"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, f.FACILITY_NAME, s.LAST_CALIBRATION_DATE, DATEDIFF('day', s.LAST_CALIBRATION_DATE, CURRENT_DATE()) AS DAYS_SINCE_CALIBRATION FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE DATEDIFF('day', s.LAST_CALIBRATION_DATE, CURRENT_DATE()) > 180 ORDER BY DAYS_SINCE_CALIBRATION DESC",
        "narration": "Sensors overdue for calibration (>180 days)."
    },
    {
        "keywords": ["total", "sensor"],
        "sql": "SELECT COUNT(*) AS TOTAL_SENSORS FROM GEOTECH.CORE.SENSORS",
        "narration": "Total number of sensors in the system."
    },
    {
        "keywords": ["threshold", "sensor"],
        "sql": "SELECT SENSOR_ID, SENSOR_TYPE, ZONE, DESIGN_THRESHOLD_VALUE, DESIGN_THRESHOLD_UNIT FROM GEOTECH.CORE.SENSORS WHERE DESIGN_THRESHOLD_VALUE IS NOT NULL ORDER BY DESIGN_THRESHOLD_VALUE DESC LIMIT 15",
        "narration": "Sensors with their design thresholds."
    },
    # --- SENSOR READINGS ---
    {
        "keywords": ["latest", "reading"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, r.READING_TS, r.READING_VALUE, s.DESIGN_THRESHOLD_UNIT AS UNIT, r.DATA_QUALITY_FLAG FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID QUALIFY ROW_NUMBER() OVER (PARTITION BY r.SENSOR_ID ORDER BY r.READING_TS DESC) = 1 ORDER BY r.READING_TS DESC LIMIT 20",
        "narration": "Latest reading from each sensor."
    },
    {
        "keywords": ["suspect", "reading"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, r.READING_TS, r.READING_VALUE, s.DESIGN_THRESHOLD_UNIT AS UNIT FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'SUSPECT' ORDER BY r.READING_TS DESC LIMIT 20",
        "narration": "Most recent suspect-flagged readings."
    },
    {
        "keywords": ["missing", "data", "reading"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, COUNT(*) AS MISSING_COUNT FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'MISSING' GROUP BY r.SENSOR_ID, s.SENSOR_TYPE ORDER BY MISSING_COUNT DESC LIMIT 15",
        "narration": "Sensors with the most missing data readings."
    },
    {
        "keywords": ["data", "quality", "summary"],
        "sql": "SELECT DATA_QUALITY_FLAG, COUNT(*) AS READING_COUNT, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS PERCENTAGE FROM GEOTECH.CORE.SENSOR_READINGS GROUP BY DATA_QUALITY_FLAG ORDER BY READING_COUNT DESC",
        "narration": "Data quality flag distribution across all readings."
    },
    {
        "keywords": ["reading", "count", "sensor"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, COUNT(r.READING_ID) AS READING_COUNT FROM GEOTECH.CORE.SENSORS s LEFT JOIN GEOTECH.CORE.SENSOR_READINGS r ON s.SENSOR_ID = r.SENSOR_ID GROUP BY s.SENSOR_ID, s.SENSOR_TYPE ORDER BY READING_COUNT DESC LIMIT 15",
        "narration": "Number of readings per sensor."
    },
    {
        "keywords": ["reading", "per", "day"],
        "sql": "SELECT DATE_TRUNC('day', READING_TS) AS READ_DATE, COUNT(*) AS READINGS FROM GEOTECH.CORE.SENSOR_READINGS WHERE READING_TS >= DATEADD('day', -30, CURRENT_TIMESTAMP()) GROUP BY READ_DATE ORDER BY READ_DATE",
        "narration": "Daily reading counts over the last 30 days."
    },
    {
        "keywords": ["max", "reading", "value"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(MAX(r.READING_VALUE),3) AS MAX_VALUE, s.DESIGN_THRESHOLD_UNIT AS UNIT, s.DESIGN_THRESHOLD_VALUE FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'NORMAL' GROUP BY s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, s.DESIGN_THRESHOLD_UNIT, s.DESIGN_THRESHOLD_VALUE ORDER BY MAX_VALUE DESC LIMIT 15",
        "narration": "Sensors with highest recorded values."
    },
    # --- PATTERN TRIGGERED ---
    {
        "keywords": ["pattern", "triggered", "count"],
        "sql": "SELECT PATTERN_TRIGGERED, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY PATTERN_TRIGGERED ORDER BY CASE_COUNT DESC",
        "narration": "Cases grouped by detection pattern type."
    },
    {
        "keywords": ["pattern", "distribution"],
        "sql": "SELECT PATTERN_TRIGGERED, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY PATTERN_TRIGGERED ORDER BY CASE_COUNT DESC",
        "narration": "Distribution of triggered detection patterns."
    },
    {
        "keywords": ["sustained", "trend"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, SEVERITY, DAYS_TO_THRESHOLD FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE PATTERN_TRIGGERED = 'SUSTAINED_TREND' ORDER BY RISK_SCORE DESC",
        "narration": "Cases triggered by sustained trend pattern."
    },
    {
        "keywords": ["rate", "change", "spike"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, SEVERITY, DAYS_TO_THRESHOLD FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE PATTERN_TRIGGERED = 'RATE_OF_CHANGE_SPIKE' ORDER BY RISK_SCORE DESC",
        "narration": "Cases triggered by rate-of-change spike."
    },
    {
        "keywords": ["threshold", "approach"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, DAYS_TO_THRESHOLD FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE PATTERN_TRIGGERED = 'THRESHOLD_APPROACH' ORDER BY DAYS_TO_THRESHOLD ASC",
        "narration": "Cases approaching design threshold."
    },
    {
        "keywords": ["days", "to", "threshold"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, DAYS_TO_THRESHOLD, RISK_SCORE, SEVERITY FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE DAYS_TO_THRESHOLD IS NOT NULL ORDER BY DAYS_TO_THRESHOLD ASC LIMIT 10",
        "narration": "Cases closest to reaching their threshold."
    },
    # --- ACTIONS & ASSIGNMENTS ---
    {
        "keywords": ["action", "count"],
        "sql": "SELECT FINAL_ACTION, COUNT(*) AS ACTION_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NOT NULL GROUP BY FINAL_ACTION ORDER BY ACTION_COUNT DESC",
        "narration": "Distribution of final actions taken."
    },
    {
        "keywords": ["recommended", "action"],
        "sql": "SELECT RECOMMENDED_ACTION, COUNT(*) AS COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY RECOMMENDED_ACTION ORDER BY COUNT DESC",
        "narration": "Distribution of recommended actions."
    },
    {
        "keywords": ["emergency", "escalation"],
        "sql": "SELECT e.ESCALATION_ID, e.CASE_ID, f.FACILITY_NAME, e.ESCALATION_TS, e.NOTIFIED_PERSONNEL, e.ACKNOWLEDGED FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e JOIN GEOTECH.CORE.FACILITIES f ON e.FACILITY_ID = f.FACILITY_ID ORDER BY e.ESCALATION_TS DESC",
        "narration": "Emergency escalation log entries."
    },
    {
        "keywords": ["unacknowledged", "escalation"],
        "sql": "SELECT e.ESCALATION_ID, e.CASE_ID, f.FACILITY_NAME, e.ESCALATION_TS, e.NOTIFIED_PERSONNEL FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e JOIN GEOTECH.CORE.FACILITIES f ON e.FACILITY_ID = f.FACILITY_ID WHERE e.ACKNOWLEDGED = FALSE ORDER BY e.ESCALATION_TS DESC",
        "narration": "Unacknowledged emergency escalations."
    },
    {
        "keywords": ["escalation", "per", "engineer"],
        "sql": "SELECT e.NOTIFIED_PERSONNEL, COUNT(*) AS ESCALATION_COUNT FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e GROUP BY e.NOTIFIED_PERSONNEL ORDER BY ESCALATION_COUNT DESC",
        "narration": "Escalations dispatched per engineer."
    },
    {
        "keywords": ["assigned", "engineer"],
        "sql": "SELECT ASSIGNED_ENGINEER, COUNT(*) AS CASE_COUNT, ROUND(AVG(RISK_SCORE), 2) AS AVG_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE ASSIGNED_ENGINEER IS NOT NULL GROUP BY ASSIGNED_ENGINEER ORDER BY CASE_COUNT DESC",
        "narration": "Cases assigned per engineer with average risk."
    },
    {
        "keywords": ["pending", "action", "unresolved"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, SEVERITY, RISK_SCORE, RECOMMENDED_ACTION, DETECTED_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NULL ORDER BY RISK_SCORE DESC",
        "narration": "Cases still pending final action."
    },
    # --- INSPECTIONS ---
    {
        "keywords": ["inspection", "log"],
        "sql": "SELECT i.INSPECTION_ID, f.FACILITY_NAME, i.INSPECTION_DATE, i.INSPECTOR_NAME, i.INSPECTION_TYPE, i.FOLLOW_UP_REQUIRED FROM GEOTECH.CORE.INSPECTION_LOG i JOIN GEOTECH.CORE.FACILITIES f ON i.FACILITY_ID = f.FACILITY_ID ORDER BY i.INSPECTION_DATE DESC LIMIT 15",
        "narration": "Recent inspection log entries."
    },
    {
        "keywords": ["inspection", "type", "count"],
        "sql": "SELECT INSPECTION_TYPE, COUNT(*) AS INSPECTION_COUNT FROM GEOTECH.CORE.INSPECTION_LOG GROUP BY INSPECTION_TYPE ORDER BY INSPECTION_COUNT DESC",
        "narration": "Inspections grouped by type."
    },
    {
        "keywords": ["follow", "up", "required"],
        "sql": "SELECT i.INSPECTION_ID, f.FACILITY_NAME, i.INSPECTION_DATE, i.INSPECTOR_NAME, i.FINDINGS FROM GEOTECH.CORE.INSPECTION_LOG i JOIN GEOTECH.CORE.FACILITIES f ON i.FACILITY_ID = f.FACILITY_ID WHERE i.FOLLOW_UP_REQUIRED = TRUE ORDER BY i.INSPECTION_DATE DESC",
        "narration": "Inspections requiring follow-up."
    },
    {
        "keywords": ["inspection", "per", "facility"],
        "sql": "SELECT f.FACILITY_NAME, COUNT(*) AS INSPECTION_COUNT, MAX(i.INSPECTION_DATE) AS LAST_INSPECTION FROM GEOTECH.CORE.INSPECTION_LOG i JOIN GEOTECH.CORE.FACILITIES f ON i.FACILITY_ID = f.FACILITY_ID GROUP BY f.FACILITY_NAME ORDER BY INSPECTION_COUNT DESC",
        "narration": "Inspection count per facility."
    },
    {
        "keywords": ["triggered", "inspection"],
        "sql": "SELECT i.INSPECTION_ID, f.FACILITY_NAME, i.INSPECTION_DATE, i.INSPECTOR_NAME, i.FINDINGS FROM GEOTECH.CORE.INSPECTION_LOG i JOIN GEOTECH.CORE.FACILITIES f ON i.FACILITY_ID = f.FACILITY_ID WHERE i.INSPECTION_TYPE = 'TRIGGERED' ORDER BY i.INSPECTION_DATE DESC",
        "narration": "All triggered inspections."
    },
    # --- PERSONNEL ---
    {
        "keywords": ["personnel", "list", "engineer"],
        "sql": "SELECT p.ENGINEER_ID, p.NAME, p.ROLE, f.FACILITY_NAME, p.ON_CALL FROM GEOTECH.CORE.PERSONNEL p JOIN GEOTECH.CORE.FACILITIES f ON p.FACILITY_ID = f.FACILITY_ID ORDER BY p.NAME",
        "narration": "All personnel with their assigned facilities."
    },
    {
        "keywords": ["on", "call"],
        "sql": "SELECT p.NAME, p.ROLE, f.FACILITY_NAME FROM GEOTECH.CORE.PERSONNEL p JOIN GEOTECH.CORE.FACILITIES f ON p.FACILITY_ID = f.FACILITY_ID WHERE p.ON_CALL = TRUE ORDER BY p.NAME",
        "narration": "Personnel currently on call."
    },
    {
        "keywords": ["role", "count", "personnel"],
        "sql": "SELECT ROLE, COUNT(*) AS PERSON_COUNT FROM GEOTECH.CORE.PERSONNEL GROUP BY ROLE ORDER BY PERSON_COUNT DESC",
        "narration": "Personnel count by role."
    },
    {
        "keywords": ["engineer", "workload"],
        "sql": "SELECT p.NAME, p.ROLE, COUNT(a.CASE_ID) AS ACTIVE_CASES, ROUND(AVG(a.RISK_SCORE), 2) AS AVG_CASE_RISK FROM GEOTECH.CORE.PERSONNEL p LEFT JOIN GEOTECH.CORE.GEOTECH_AUDIT a ON p.NAME = a.ASSIGNED_ENGINEER GROUP BY p.NAME, p.ROLE ORDER BY ACTIVE_CASES DESC",
        "narration": "Engineer workload — cases assigned per person."
    },
    # --- CROSS-TABLE ANALYTICS ---
    {
        "keywords": ["facility", "summary", "overview"],
        "sql": "SELECT f.FACILITY_NAME, f.RISK_CLASSIFICATION, COUNT(DISTINCT s.SENSOR_ID) AS SENSORS, COUNT(DISTINCT a.CASE_ID) AS AUDIT_CASES, COALESCE(ROUND(AVG(a.RISK_SCORE), 2), 0) AS AVG_RISK FROM GEOTECH.CORE.FACILITIES f LEFT JOIN GEOTECH.CORE.SENSORS s ON f.FACILITY_ID = s.FACILITY_ID LEFT JOIN GEOTECH.CORE.GEOTECH_AUDIT a ON f.FACILITY_ID = a.FACILITY_ID GROUP BY f.FACILITY_NAME, f.RISK_CLASSIFICATION ORDER BY AVG_RISK DESC",
        "narration": "Facility summary with sensor count and audit cases."
    },
    {
        "keywords": ["zone", "summary"],
        "sql": "SELECT a.ZONE, COUNT(*) AS CASES, ROUND(AVG(a.RISK_SCORE), 2) AS AVG_RISK, SUM(CASE WHEN a.SEVERITY = 'CRITICAL' THEN 1 ELSE 0 END) AS CRITICAL_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT a GROUP BY a.ZONE ORDER BY AVG_RISK DESC",
        "narration": "Zone-level summary with case counts and risk."
    },
    {
        "keywords": ["sensor", "most", "case"],
        "sql": "SELECT a.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, COUNT(*) AS CASE_COUNT, ROUND(AVG(a.RISK_SCORE), 2) AS AVG_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.SENSORS s ON a.SENSOR_ID = s.SENSOR_ID GROUP BY a.SENSOR_ID, s.SENSOR_TYPE, s.ZONE ORDER BY CASE_COUNT DESC LIMIT 10",
        "narration": "Sensors with the most audit cases."
    },
    {
        "keywords": ["recent", "case"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, SEVERITY, RISK_SCORE, DETECTED_TS, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY DETECTED_TS DESC LIMIT 10",
        "narration": "Most recently detected cases."
    },
    {
        "keywords": ["case", "per", "facility"],
        "sql": "SELECT f.FACILITY_NAME, COUNT(*) AS CASE_COUNT, SUM(CASE WHEN a.SEVERITY = 'CRITICAL' THEN 1 ELSE 0 END) AS CRITICAL, SUM(CASE WHEN a.SEVERITY = 'HIGH' THEN 1 ELSE 0 END) AS HIGH FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID GROUP BY f.FACILITY_NAME ORDER BY CASE_COUNT DESC",
        "narration": "Case count per facility with severity breakdown."
    },
    {
        "keywords": ["escalation", "timeline"],
        "sql": "SELECT DATE_TRUNC('day', ESCALATION_TS) AS ESC_DATE, COUNT(*) AS ESCALATIONS FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG GROUP BY ESC_DATE ORDER BY ESC_DATE",
        "narration": "Escalation timeline — daily counts."
    },
    {
        "keywords": ["how", "many", "case"],
        "sql": "SELECT COUNT(*) AS TOTAL_CASES FROM GEOTECH.CORE.GEOTECH_AUDIT",
        "narration": "Total number of audit cases in the system."
    },
    {
        "keywords": ["how", "many", "sensor"],
        "sql": "SELECT COUNT(*) AS TOTAL_SENSORS FROM GEOTECH.CORE.SENSORS",
        "narration": "Total number of sensors."
    },
    {
        "keywords": ["how", "many", "facility"],
        "sql": "SELECT COUNT(*) AS TOTAL_FACILITIES FROM GEOTECH.CORE.FACILITIES",
        "narration": "Total number of facilities."
    },
    {
        "keywords": ["how", "many", "escalation"],
        "sql": "SELECT COUNT(*) AS TOTAL_ESCALATIONS FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG",
        "narration": "Total number of emergency escalations."
    },
    {
        "keywords": ["how", "many", "inspection"],
        "sql": "SELECT COUNT(*) AS TOTAL_INSPECTIONS FROM GEOTECH.CORE.INSPECTION_LOG",
        "narration": "Total number of inspections."
    },
    # --- LLM RATIONALE ---
    {
        "keywords": ["rationale", "explanation"],
        "sql": "SELECT CASE_ID, SEVERITY, RISK_SCORE, LLM_RATIONALE FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NOT NULL ORDER BY RISK_SCORE DESC LIMIT 10",
        "narration": "AI-generated rationale for top risk cases."
    },
    # --- CROSS-SENSOR CORRELATION ---
    {
        "keywords": ["cross", "sensor", "correlation"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, DAYS_TO_THRESHOLD FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE PATTERN_TRIGGERED = 'CROSS_SENSOR_CORRELATION' ORDER BY RISK_SCORE DESC",
        "narration": "Cases triggered by cross-sensor correlation."
    },
    {
        "keywords": ["weir", "flow"],
        "sql": "SELECT s.SENSOR_ID, f.FACILITY_NAME, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, s.STATUS, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.SENSOR_TYPE = 'WEIR_FLOW' ORDER BY s.SENSOR_ID",
        "narration": "All weir flow sensors."
    },
    {
        "keywords": ["sensor", "status"],
        "sql": "SELECT STATUS, COUNT(*) AS SENSOR_COUNT, COUNT(DISTINCT SENSOR_TYPE) AS SENSOR_TYPES, LISTAGG(DISTINCT SENSOR_TYPE, ', ') AS TYPES FROM GEOTECH.CORE.SENSORS GROUP BY STATUS ORDER BY SENSOR_COUNT DESC",
        "narration": "Sensor operational status by type."
    },
    {
        "keywords": ["depth", "sensor"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, s.DEPTH_M, f.FACILITY_NAME FROM GEOTECH.CORE.SENSORS s JOIN GEOTECH.CORE.FACILITIES f ON s.FACILITY_ID = f.FACILITY_ID WHERE s.DEPTH_M IS NOT NULL ORDER BY s.DEPTH_M DESC LIMIT 20",
        "narration": "Deepest installed sensors."
    },
    {
        "keywords": ["regulatory", "body"],
        "sql": "SELECT REGULATORY_BODY, COUNT(*) AS FACILITY_COUNT, LISTAGG(FACILITY_NAME, '; ') AS FACILITIES FROM GEOTECH.CORE.FACILITIES GROUP BY REGULATORY_BODY ORDER BY FACILITY_COUNT DESC",
        "narration": "Facilities grouped by regulatory body."
    },
    # --- DATA QUALITY GAP ---
    {
        "keywords": ["data", "quality", "gap"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, RISK_SCORE, DETECTED_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE PATTERN_TRIGGERED = 'DATA_QUALITY_GAP' ORDER BY DETECTED_TS DESC",
        "narration": "Cases triggered by data quality gaps."
    },
    # =========================================================================
    # $geotech-drift-scan — deterministic detection (baseline, regression,
    # rate-of-change, threshold extrapolation, cross-sensor correlation)
    # =========================================================================
    {
        "skill": "drift",
        "keywords": ["baseline", "mean"],
        "sql": "WITH w AS (SELECT r.SENSOR_ID, r.READING_VALUE, CASE WHEN r.READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) THEN 'RECENT' ELSE 'BASELINE' END AS WINDOW_PART FROM GEOTECH.CORE.SENSOR_READINGS r WHERE r.DATA_QUALITY_FLAG IN ('NORMAL','SUSPECT')) SELECT SENSOR_ID, ROUND(AVG(CASE WHEN WINDOW_PART='BASELINE' THEN READING_VALUE END),3) AS BASELINE_MEAN, ROUND(STDDEV(CASE WHEN WINDOW_PART='BASELINE' THEN READING_VALUE END),3) AS BASELINE_STDDEV, ROUND(AVG(CASE WHEN WINDOW_PART='RECENT' THEN READING_VALUE END),3) AS RECENT_MEAN, ROUND(AVG(CASE WHEN WINDOW_PART='RECENT' THEN READING_VALUE END) - AVG(CASE WHEN WINDOW_PART='BASELINE' THEN READING_VALUE END),3) AS MEAN_SHIFT FROM w GROUP BY SENSOR_ID HAVING BASELINE_STDDEV IS NOT NULL AND RECENT_MEAN IS NOT NULL ORDER BY ABS(MEAN_SHIFT) DESC LIMIT 20",
        "narration": "Baseline vs recent 60-day mean per sensor."
    },
    {
        "skill": "drift",
        "keywords": ["regression", "slope"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),5) AS SLOPE_PER_DAY, ROUND(REGR_R2(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),3) AS R_SQUARED, COUNT(*) AS READINGS FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'NORMAL' AND r.READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) GROUP BY r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE HAVING COUNT(*) >= 10 ORDER BY ABS(SLOPE_PER_DAY) DESC LIMIT 20",
        "narration": "60-day linear regression slope per sensor."
    },
    {
        "skill": "drift",
        "keywords": ["r2", "fit"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(REGR_R2(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),3) AS R_SQUARED, ROUND(REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),5) AS SLOPE_PER_DAY FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'NORMAL' AND r.READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) GROUP BY r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE HAVING COUNT(*) >= 10 AND REGR_R2(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)) > 0.5 ORDER BY R_SQUARED DESC LIMIT 20",
        "narration": "Sensors with a statistically strong trend (R-squared > 0.5)."
    },
    {
        "skill": "drift",
        "keywords": ["trending", "sensor"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, CASE WHEN REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)) > 0 THEN 'RISING' ELSE 'FALLING' END AS DIRECTION, ROUND(REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),5) AS SLOPE_PER_DAY, ROUND(REGR_R2(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)),3) AS R_SQUARED FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG = 'NORMAL' AND r.READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) GROUP BY r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE HAVING COUNT(*) >= 10 ORDER BY ABS(SLOPE_PER_DAY) DESC LIMIT 20",
        "narration": "Trend direction per sensor over the 60-day window."
    },
    {
        "skill": "drift",
        "keywords": ["sigma", "deviation"],
        "sql": "WITH stats AS (SELECT SENSOR_ID, AVG(READING_VALUE) AS MU, STDDEV(READING_VALUE) AS SD FROM GEOTECH.CORE.SENSOR_READINGS WHERE DATA_QUALITY_FLAG = 'NORMAL' GROUP BY SENSOR_ID), recent AS (SELECT SENSOR_ID, MAX(READING_VALUE) AS PEAK FROM GEOTECH.CORE.SENSOR_READINGS WHERE DATA_QUALITY_FLAG = 'NORMAL' AND READING_TS >= DATEADD('day', -7, CURRENT_TIMESTAMP()) GROUP BY SENSOR_ID) SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(st.MU,3) AS HISTORICAL_MEAN, ROUND(st.SD,3) AS HISTORICAL_STDDEV, ROUND(r.PEAK,3) AS PEAK_LAST_7D, ROUND((r.PEAK - st.MU)/NULLIF(st.SD,0),2) AS SIGMA_ABOVE_MEAN FROM recent r JOIN stats st ON r.SENSOR_ID = st.SENSOR_ID JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE st.SD > 0 ORDER BY SIGMA_ABOVE_MEAN DESC LIMIT 20",
        "narration": "Rate-of-change spike magnitude in sigma above historical mean."
    },
    {
        "skill": "drift",
        "keywords": ["rolling", "delta"],
        "sql": "WITH daily AS (SELECT SENSOR_ID, DATE_TRUNC('day', READING_TS) AS D, AVG(READING_VALUE) AS V FROM GEOTECH.CORE.SENSOR_READINGS WHERE DATA_QUALITY_FLAG = 'NORMAL' AND READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) GROUP BY SENSOR_ID, D), d2 AS (SELECT SENSOR_ID, D, V, V - LAG(V, 7) OVER (PARTITION BY SENSOR_ID ORDER BY D) AS DELTA_7D FROM daily) SELECT SENSOR_ID, ROUND(MAX(ABS(DELTA_7D)),3) AS MAX_7DAY_DELTA, ROUND(AVG(ABS(DELTA_7D)),3) AS AVG_7DAY_DELTA FROM d2 WHERE DELTA_7D IS NOT NULL GROUP BY SENSOR_ID ORDER BY MAX_7DAY_DELTA DESC LIMIT 20",
        "narration": "Maximum 7-day rolling delta per sensor."
    },
    {
        "skill": "drift",
        "keywords": ["extrapolate", "projection"],
        "sql": "WITH t AS (SELECT r.SENSOR_ID, REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)) AS SLOPE, REGR_R2(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)) AS R2, MAX(r.READING_VALUE) AS LATEST_VAL FROM GEOTECH.CORE.SENSOR_READINGS r WHERE r.DATA_QUALITY_FLAG='NORMAL' AND r.READING_TS >= DATEADD('day',-60,CURRENT_TIMESTAMP()) GROUP BY r.SENSOR_ID HAVING COUNT(*) >= 10) SELECT t.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(t.SLOPE,5) AS SLOPE_PER_DAY, ROUND(t.R2,3) AS R_SQUARED, s.DESIGN_THRESHOLD_VALUE, ROUND(t.LATEST_VAL,3) AS CURRENT_VALUE, CASE WHEN t.SLOPE > 0 AND s.DESIGN_THRESHOLD_VALUE > t.LATEST_VAL THEN CEIL((s.DESIGN_THRESHOLD_VALUE - t.LATEST_VAL)/t.SLOPE) END AS PROJECTED_DAYS_TO_THRESHOLD FROM t JOIN GEOTECH.CORE.SENSORS s ON t.SENSOR_ID = s.SENSOR_ID WHERE t.R2 > 0.5 AND t.SLOPE > 0 AND s.DESIGN_THRESHOLD_VALUE IS NOT NULL ORDER BY PROJECTED_DAYS_TO_THRESHOLD NULLS LAST LIMIT 20",
        "narration": "Threshold extrapolation for sensors with R-squared > 0.5 and rising trend."
    },
    {
        "skill": "drift",
        "keywords": ["eligible", "scan"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, COUNT(r.READING_ID) AS QUALIFYING_READINGS, DATEDIFF('day', MIN(r.READING_TS), MAX(r.READING_TS)) AS DAYS_OF_HISTORY, CASE WHEN DATEDIFF('day', MIN(r.READING_TS), MAX(r.READING_TS)) >= 60 THEN 'ELIGIBLE' ELSE 'INSUFFICIENT_HISTORY' END AS SCAN_ELIGIBILITY FROM GEOTECH.CORE.SENSORS s LEFT JOIN GEOTECH.CORE.SENSOR_READINGS r ON s.SENSOR_ID = r.SENSOR_ID AND r.DATA_QUALITY_FLAG IN ('NORMAL','SUSPECT') GROUP BY s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE ORDER BY DAYS_OF_HISTORY DESC NULLS LAST LIMIT 25",
        "narration": "Drift-scan eligibility: sensors with at least 60 days of usable readings."
    },
    {
        "skill": "drift",
        "keywords": ["last", "14", "days"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, SUM(CASE WHEN r.DATA_QUALITY_FLAG='MISSING' THEN 1 ELSE 0 END) AS MISSING_14D, SUM(CASE WHEN r.DATA_QUALITY_FLAG='SUSPECT' THEN 1 ELSE 0 END) AS SUSPECT_14D, COUNT(*) AS TOTAL_14D FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.READING_TS >= DATEADD('day', -14, CURRENT_TIMESTAMP()) GROUP BY r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE HAVING MISSING_14D + SUSPECT_14D > 0 ORDER BY MISSING_14D + SUSPECT_14D DESC LIMIT 20",
        "narration": "Data-quality gap counts in the last 14 days (drift-scan input)."
    },
    {
        "skill": "drift",
        "keywords": ["correlated", "movement"],
        "sql": "WITH slopes AS (SELECT s.FACILITY_ID, s.ZONE, r.SENSOR_ID, REGR_SLOPE(r.READING_VALUE, DATEDIFF('day','2020-01-01'::DATE, r.READING_TS)) AS SLOPE FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG='NORMAL' AND r.READING_TS >= DATEADD('day',-60,CURRENT_TIMESTAMP()) GROUP BY s.FACILITY_ID, s.ZONE, r.SENSOR_ID HAVING COUNT(*) >= 10) SELECT f.FACILITY_NAME, sl.ZONE, COUNT(*) AS SENSORS_IN_ZONE, SUM(CASE WHEN sl.SLOPE > 0 THEN 1 ELSE 0 END) AS RISING, SUM(CASE WHEN sl.SLOPE < 0 THEN 1 ELSE 0 END) AS FALLING, GREATEST(SUM(CASE WHEN sl.SLOPE > 0 THEN 1 ELSE 0 END), SUM(CASE WHEN sl.SLOPE < 0 THEN 1 ELSE 0 END)) AS SAME_DIRECTION_COUNT FROM slopes sl JOIN GEOTECH.CORE.FACILITIES f ON sl.FACILITY_ID = f.FACILITY_ID GROUP BY f.FACILITY_NAME, sl.ZONE HAVING COUNT(*) > 1 ORDER BY SAME_DIRECTION_COUNT DESC LIMIT 20",
        "narration": "Cross-sensor correlation: sensors moving the same direction per facility and zone."
    },
    {
        "skill": "drift",
        "keywords": ["drift", "scan", "risk", "weight"],
        "sql": "SELECT PATTERN_TRIGGERED, CASE PATTERN_TRIGGERED WHEN 'CROSS_SENSOR_CORRELATION' THEN 45 WHEN 'THRESHOLD_APPROACH' THEN 35 WHEN 'RATE_OF_CHANGE_SPIKE' THEN 30 WHEN 'SUSTAINED_TREND' THEN 15 WHEN 'DATA_QUALITY_GAP' THEN 10 END AS SKILL_WEIGHT, COUNT(*) AS CASE_COUNT, ROUND(AVG(RISK_SCORE),2) AS AVG_ACTUAL_RISK_SCORE FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY PATTERN_TRIGGERED ORDER BY SKILL_WEIGHT DESC NULLS LAST",
        "narration": "Drift-scan risk weights per pattern vs actual recorded risk scores."
    },
    {
        "skill": "drift",
        "keywords": ["severity", "band"],
        "sql": "SELECT CASE_ID, RISK_SCORE, SEVERITY AS RECORDED_SEVERITY, CASE WHEN RISK_SCORE >= 70 THEN 'CRITICAL' WHEN RISK_SCORE >= 50 THEN 'HIGH' WHEN RISK_SCORE >= 25 THEN 'MEDIUM' ELSE 'LOW' END AS EXPECTED_SEVERITY, CASE WHEN SEVERITY = CASE WHEN RISK_SCORE >= 70 THEN 'CRITICAL' WHEN RISK_SCORE >= 50 THEN 'HIGH' WHEN RISK_SCORE >= 25 THEN 'MEDIUM' ELSE 'LOW' END THEN 'MATCH' ELSE 'MISMATCH' END AS BAND_CHECK FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY RISK_SCORE DESC",
        "narration": "Severity band verification against the drift-scan thresholds."
    },
    {
        "skill": "drift",
        "keywords": ["percent", "threshold"],
        "sql": "WITH latest AS (SELECT SENSOR_ID, READING_VALUE, READING_TS FROM GEOTECH.CORE.SENSOR_READINGS WHERE DATA_QUALITY_FLAG='NORMAL' QUALIFY ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY READING_TS DESC) = 1) SELECT l.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, ROUND(l.READING_VALUE,3) AS CURRENT_VALUE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, ROUND(100.0 * l.READING_VALUE / NULLIF(s.DESIGN_THRESHOLD_VALUE,0), 1) AS PCT_OF_THRESHOLD FROM latest l JOIN GEOTECH.CORE.SENSORS s ON l.SENSOR_ID = s.SENSOR_ID WHERE s.DESIGN_THRESHOLD_VALUE IS NOT NULL ORDER BY PCT_OF_THRESHOLD DESC LIMIT 20",
        "narration": "Latest reading as a percentage of each sensor's design threshold."
    },
    {
        "skill": "drift",
        "keywords": ["exceed", "threshold"],
        "sql": "SELECT r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, COUNT(*) AS EXCEEDANCE_READINGS, ROUND(MAX(r.READING_VALUE),3) AS PEAK_VALUE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT, MAX(r.READING_TS) AS LAST_EXCEEDANCE FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.DATA_QUALITY_FLAG='NORMAL' AND s.DESIGN_THRESHOLD_VALUE IS NOT NULL AND r.READING_VALUE > s.DESIGN_THRESHOLD_VALUE GROUP BY r.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, s.DESIGN_THRESHOLD_VALUE, s.DESIGN_THRESHOLD_UNIT ORDER BY EXCEEDANCE_READINGS DESC LIMIT 20",
        "narration": "Sensors with readings above their design threshold."
    },
    {
        "skill": "drift",
        "keywords": ["stale", "sensor"],
        "sql": "SELECT s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, s.STATUS, MAX(r.READING_TS) AS LAST_READING_TS, DATEDIFF('day', MAX(r.READING_TS), CURRENT_TIMESTAMP()) AS DAYS_SINCE_LAST_READING FROM GEOTECH.CORE.SENSORS s LEFT JOIN GEOTECH.CORE.SENSOR_READINGS r ON s.SENSOR_ID = r.SENSOR_ID GROUP BY s.SENSOR_ID, s.SENSOR_TYPE, s.ZONE, s.STATUS ORDER BY DAYS_SINCE_LAST_READING DESC NULLS FIRST LIMIT 20",
        "narration": "Sensors with the most stale data (largest gap since last reading)."
    },
    {
        "skill": "drift",
        "keywords": ["volume", "60"],
        "sql": "SELECT s.SENSOR_TYPE, COUNT(r.READING_ID) AS READING_COUNT, COUNT(DISTINCT r.SENSOR_ID) AS SENSORS_REPORTING, ROUND(COUNT(r.READING_ID)*1.0/NULLIF(COUNT(DISTINCT r.SENSOR_ID),0),1) AS AVG_READINGS_PER_SENSOR FROM GEOTECH.CORE.SENSOR_READINGS r JOIN GEOTECH.CORE.SENSORS s ON r.SENSOR_ID = s.SENSOR_ID WHERE r.READING_TS >= DATEADD('day', -60, CURRENT_TIMESTAMP()) GROUP BY s.SENSOR_TYPE ORDER BY READING_COUNT DESC",
        "narration": "60-day reading volume by sensor type."
    },
    {
        "skill": "drift",
        "keywords": ["coverage", "flagged"],
        "sql": "SELECT COUNT(DISTINCT s.SENSOR_ID) AS TOTAL_SENSORS, COUNT(DISTINCT a.SENSOR_ID) AS FLAGGED_SENSORS, COUNT(DISTINCT s.SENSOR_ID) - COUNT(DISTINCT a.SENSOR_ID) AS CLEAN_SENSORS, ROUND(100.0 * COUNT(DISTINCT a.SENSOR_ID)/NULLIF(COUNT(DISTINCT s.SENSOR_ID),0),1) AS PCT_FLAGGED FROM GEOTECH.CORE.SENSORS s LEFT JOIN GEOTECH.CORE.GEOTECH_AUDIT a ON s.SENSOR_ID = a.SENSOR_ID",
        "narration": "Drift-scan coverage: flagged vs clean sensors."
    },

    # =========================================================================
    # $geotech-risk-synthesis — LLM reasoning scoped to flagged cases
    # =========================================================================
    {
        "skill": "risk",
        "keywords": ["unresolved", "synthesis"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, PATTERN_TRIGGERED, DAYS_TO_THRESHOLD, RISK_SCORE, SEVERITY, DETECTED_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NULL ORDER BY RISK_SCORE DESC",
        "narration": "Synthesis queue: flagged cases still awaiting a rationale."
    },
    {
        "skill": "risk",
        "keywords": ["synthesis", "input"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, s.SENSOR_TYPE, a.ZONE, a.PATTERN_TRIGGERED, a.DAYS_TO_THRESHOLD, a.RISK_SCORE, a.SEVERITY, s.LAST_CALIBRATION_DATE FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID JOIN GEOTECH.CORE.SENSORS s ON a.SENSOR_ID = s.SENSOR_ID ORDER BY a.RISK_SCORE DESC",
        "narration": "Risk-synthesis input context joined per flagged case."
    },
    {
        "skill": "risk",
        "keywords": ["inspection", "findings", "flagged"],
        "sql": "SELECT DISTINCT a.CASE_ID, f.FACILITY_NAME, a.SEVERITY, i.INSPECTION_DATE, i.INSPECTION_TYPE, i.FINDINGS FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID JOIN GEOTECH.CORE.INSPECTION_LOG i ON a.FACILITY_ID = i.FACILITY_ID WHERE i.INSPECTION_DATE >= DATEADD('day', -180, CURRENT_DATE()) ORDER BY i.INSPECTION_DATE DESC LIMIT 25",
        "narration": "Recent inspection findings available to risk synthesis for flagged facilities."
    },
    {
        "skill": "risk",
        "keywords": ["extreme", "correlation", "rule"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, a.ZONE, a.DAYS_TO_THRESHOLD, a.RISK_SCORE, a.SEVERITY, a.RECOMMENDED_ACTION, CASE WHEN a.DAYS_TO_THRESHOLD < 30 THEN 'EMERGENCY_ESCALATION' ELSE 'URGENT_INSPECTION' END AS SKILL_MINIMUM_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID WHERE a.PATTERN_TRIGGERED = 'CROSS_SENSOR_CORRELATION' AND f.RISK_CLASSIFICATION IN ('EXTREME','HIGH') ORDER BY a.DAYS_TO_THRESHOLD NULLS LAST",
        "narration": "Cross-sensor correlation at EXTREME/HIGH facilities — minimum URGENT_INSPECTION per skill rules."
    },
    {
        "skill": "risk",
        "keywords": ["imminent", "breach"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, a.SENSOR_ID, a.ZONE, a.PATTERN_TRIGGERED, a.DAYS_TO_THRESHOLD, a.SEVERITY, a.RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID WHERE a.DAYS_TO_THRESHOLD < 14 ORDER BY a.DAYS_TO_THRESHOLD",
        "narration": "Cases under 14 days to threshold — EMERGENCY_ESCALATION regardless of facility class."
    },
    {
        "skill": "risk",
        "keywords": ["calibration", "drift"],
        "sql": "SELECT a.CASE_ID, a.SENSOR_ID, s.SENSOR_TYPE, a.ZONE, a.PATTERN_TRIGGERED, s.LAST_CALIBRATION_DATE, DATEDIFF('month', s.LAST_CALIBRATION_DATE, CURRENT_DATE()) AS MONTHS_SINCE_CALIBRATION, a.SEVERITY, a.RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.SENSORS s ON a.SENSOR_ID = s.SENSOR_ID WHERE a.PATTERN_TRIGGERED = 'SUSTAINED_TREND' AND DATEDIFF('month', s.LAST_CALIBRATION_DATE, CURRENT_DATE()) > 12 ORDER BY MONTHS_SINCE_CALIBRATION DESC",
        "narration": "Isolated sustained trends with calibration older than 12 months — possible calibration drift."
    },
    {
        "skill": "risk",
        "keywords": ["gap", "only"],
        "sql": "SELECT a.CASE_ID, a.FACILITY_ID, a.SENSOR_ID, s.SENSOR_TYPE, a.ZONE, a.RISK_SCORE, a.SEVERITY, a.RECOMMENDED_ACTION, 'SCHEDULE_INSPECTION' AS SKILL_EXPECTED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.SENSORS s ON a.SENSOR_ID = s.SENSOR_ID WHERE a.PATTERN_TRIGGERED = 'DATA_QUALITY_GAP' ORDER BY a.DETECTED_TS DESC",
        "narration": "Data-quality-gap-only cases — skill routes these to SCHEDULE_INSPECTION, not escalation."
    },
    {
        "skill": "risk",
        "keywords": ["default", "mapping"],
        "sql": "SELECT SEVERITY, CASE SEVERITY WHEN 'LOW' THEN 'MONITOR' WHEN 'MEDIUM' THEN 'SCHEDULE_INSPECTION' WHEN 'HIGH' THEN 'URGENT_INSPECTION' WHEN 'CRITICAL' THEN 'EMERGENCY_ESCALATION' END AS SKILL_DEFAULT_ACTION, RECOMMENDED_ACTION, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY SEVERITY, RECOMMENDED_ACTION ORDER BY SEVERITY, CASE_COUNT DESC",
        "narration": "Severity-to-action default mapping vs what was actually recommended."
    },
    {
        "skill": "risk",
        "keywords": ["mismatch", "recommendation"],
        "sql": "SELECT CASE_ID, SEVERITY, RECOMMENDED_ACTION, CASE SEVERITY WHEN 'LOW' THEN 'MONITOR' WHEN 'MEDIUM' THEN 'SCHEDULE_INSPECTION' WHEN 'HIGH' THEN 'URGENT_INSPECTION' WHEN 'CRITICAL' THEN 'EMERGENCY_ESCALATION' END AS EXPECTED_DEFAULT, PATTERN_TRIGGERED, DAYS_TO_THRESHOLD, RISK_SCORE FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION IS NOT NULL AND RECOMMENDED_ACTION <> CASE SEVERITY WHEN 'LOW' THEN 'MONITOR' WHEN 'MEDIUM' THEN 'SCHEDULE_INSPECTION' WHEN 'HIGH' THEN 'URGENT_INSPECTION' WHEN 'CRITICAL' THEN 'EMERGENCY_ESCALATION' END ORDER BY RISK_SCORE DESC",
        "narration": "Recommendations that deviate from the severity default (escalated or de-escalated by rule)."
    },
    {
        "skill": "risk",
        "keywords": ["rationale", "coverage"],
        "sql": "SELECT COUNT(*) AS TOTAL_CASES, SUM(CASE WHEN LLM_RATIONALE IS NOT NULL THEN 1 ELSE 0 END) AS WITH_RATIONALE, SUM(CASE WHEN LLM_RATIONALE IS NULL THEN 1 ELSE 0 END) AS MISSING_RATIONALE, ROUND(100.0*SUM(CASE WHEN LLM_RATIONALE IS NOT NULL THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS PCT_COVERAGE FROM GEOTECH.CORE.GEOTECH_AUDIT",
        "narration": "Risk-synthesis rationale coverage across all flagged cases."
    },
    {
        "skill": "risk",
        "keywords": ["contract", "violation", "rationale"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, SEVERITY, RISK_SCORE, RECOMMENDED_ACTION, DETECTED_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NULL AND RECOMMENDED_ACTION IS NOT NULL ORDER BY RISK_SCORE DESC",
        "narration": "Output-contract violations: a recommended action was set without a rationale."
    },
    {
        "skill": "risk",
        "keywords": ["rationale", "length"],
        "sql": "SELECT CASE_ID, SEVERITY, RISK_SCORE, LENGTH(LLM_RATIONALE) AS RATIONALE_CHARS, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NOT NULL ORDER BY RATIONALE_CHARS DESC LIMIT 20",
        "narration": "Rationale depth per case, longest first."
    },
    {
        "skill": "risk",
        "keywords": ["action", "risk", "classification"],
        "sql": "SELECT f.RISK_CLASSIFICATION, a.RECOMMENDED_ACTION, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID WHERE a.RECOMMENDED_ACTION IS NOT NULL GROUP BY f.RISK_CLASSIFICATION, a.RECOMMENDED_ACTION ORDER BY f.RISK_CLASSIFICATION, CASE_COUNT DESC",
        "narration": "Recommended actions broken down by facility risk classification."
    },
    {
        "skill": "risk",
        "keywords": ["action", "pattern"],
        "sql": "SELECT PATTERN_TRIGGERED, RECOMMENDED_ACTION, COUNT(*) AS CASE_COUNT, ROUND(AVG(RISK_SCORE),2) AS AVG_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION IS NOT NULL GROUP BY PATTERN_TRIGGERED, RECOMMENDED_ACTION ORDER BY CASE_COUNT DESC",
        "narration": "How each detection pattern maps to recommended actions."
    },
    {
        "skill": "risk",
        "keywords": ["extreme", "facility", "case"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, f.DAM_TYPE, a.ZONE, a.PATTERN_TRIGGERED, a.RISK_SCORE, a.SEVERITY, a.RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID WHERE f.RISK_CLASSIFICATION = 'EXTREME' ORDER BY a.RISK_SCORE DESC",
        "narration": "Flagged cases at EXTREME-classification facilities."
    },
    {
        "skill": "risk",
        "keywords": ["backlog", "severity"],
        "sql": "SELECT SEVERITY, COUNT(*) AS PENDING_SYNTHESIS, ROUND(AVG(RISK_SCORE),2) AS AVG_RISK, MIN(DETECTED_TS) AS OLDEST_DETECTION FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NULL GROUP BY SEVERITY ORDER BY AVG_RISK DESC",
        "narration": "Synthesis backlog grouped by severity."
    },
    {
        "skill": "risk",
        "keywords": ["aging", "detection"],
        "sql": "SELECT CASE_ID, SEVERITY, RISK_SCORE, DETECTED_TS, DATEDIFF('hour', DETECTED_TS, CURRENT_TIMESTAMP()) AS HOURS_SINCE_DETECTION, RECOMMENDED_ACTION, FINAL_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY HOURS_SINCE_DETECTION DESC LIMIT 20",
        "narration": "Case age since detection — oldest first."
    },

    # =========================================================================
    # $geotech-action-orchestrator — deterministic branching + auditable writes
    # =========================================================================
    {
        "skill": "action",
        "keywords": ["execution", "queue"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, SEVERITY, RISK_SCORE, RECOMMENDED_ACTION, DETECTED_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION IS NOT NULL AND FINAL_ACTION IS NULL ORDER BY RISK_SCORE DESC",
        "narration": "Orchestrator execution queue: recommended but not yet executed."
    },
    {
        "skill": "action",
        "keywords": ["branch", "mapping"],
        "sql": "SELECT RECOMMENDED_ACTION, CASE RECOMMENDED_ACTION WHEN 'MONITOR' THEN 'LOGGED_MONITORING' WHEN 'SCHEDULE_INSPECTION' THEN 'INSPECTION_SCHEDULED' WHEN 'URGENT_INSPECTION' THEN 'URGENT_INSPECTION_DISPATCHED' WHEN 'EMERGENCY_ESCALATION' THEN 'EMERGENCY_ESCALATED' END AS EXPECTED_FINAL_ACTION, COUNT(*) AS CASE_COUNT, SUM(CASE WHEN FINAL_ACTION IS NULL THEN 1 ELSE 0 END) AS STILL_PENDING FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION IS NOT NULL GROUP BY RECOMMENDED_ACTION ORDER BY CASE_COUNT DESC",
        "narration": "Deterministic branch mapping from recommended action to final action."
    },
    {
        "skill": "action",
        "keywords": ["monitor", "branch"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, SEVERITY, RISK_SCORE, FINAL_ACTION, ACTION_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION = 'MONITOR' ORDER BY RISK_SCORE DESC",
        "narration": "MONITOR branch — logged monitoring only, no downstream writes."
    },
    {
        "skill": "action",
        "keywords": ["schedule", "branch"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, a.ZONE, a.SEVERITY, a.RISK_SCORE, a.FINAL_ACTION, a.ASSIGNED_ENGINEER, p.NAME AS SITE_GEOTECH_ENGINEER, p.ON_CALL FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID LEFT JOIN GEOTECH.CORE.PERSONNEL p ON a.FACILITY_ID = p.FACILITY_ID AND p.ROLE = 'SITE_GEOTECH_ENGINEER' WHERE a.RECOMMENDED_ACTION = 'SCHEDULE_INSPECTION' ORDER BY a.RISK_SCORE DESC",
        "narration": "SCHEDULE_INSPECTION branch with the site geotech engineer the skill would assign."
    },
    {
        "skill": "action",
        "keywords": ["urgent", "branch"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, a.ZONE, a.SEVERITY, a.RISK_SCORE, a.DAYS_TO_THRESHOLD, a.FINAL_ACTION, p.NAME AS DAM_SAFETY_ENGINEER_OF_RECORD, p.EMAIL, p.PHONE FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID LEFT JOIN GEOTECH.CORE.PERSONNEL p ON a.FACILITY_ID = p.FACILITY_ID AND p.ROLE = 'DAM_SAFETY_ENGINEER_OF_RECORD' WHERE a.RECOMMENDED_ACTION = 'URGENT_INSPECTION' ORDER BY a.RISK_SCORE DESC",
        "narration": "URGENT_INSPECTION branch with the dam safety engineer of record to notify."
    },
    {
        "skill": "action",
        "keywords": ["emergency", "branch"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, a.ZONE, a.SEVERITY, a.DAYS_TO_THRESHOLD, a.FINAL_ACTION, LISTAGG(p.NAME || ' (' || p.ROLE || ')', '; ') AS NOTIFY_LIST FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID LEFT JOIN GEOTECH.CORE.PERSONNEL p ON a.FACILITY_ID = p.FACILITY_ID AND p.ROLE IN ('DAM_SAFETY_ENGINEER_OF_RECORD','OPERATIONS_MANAGER') WHERE a.RECOMMENDED_ACTION = 'EMERGENCY_ESCALATION' GROUP BY a.CASE_ID, f.FACILITY_NAME, f.RISK_CLASSIFICATION, a.ZONE, a.SEVERITY, a.DAYS_TO_THRESHOLD, a.FINAL_ACTION ORDER BY a.DAYS_TO_THRESHOLD NULLS LAST",
        "narration": "EMERGENCY_ESCALATION branch with the personnel the skill notifies."
    },
    {
        "skill": "action",
        "keywords": ["idempotent", "skip"],
        "sql": "SELECT CASE_ID, RECOMMENDED_ACTION, FINAL_ACTION, ACTION_TS, ASSIGNED_ENGINEER FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NOT NULL ORDER BY ACTION_TS DESC NULLS LAST",
        "narration": "Already-executed cases the orchestrator skips on re-run (idempotency)."
    },
    {
        "skill": "action",
        "keywords": ["orphan", "final"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, SEVERITY, RECOMMENDED_ACTION, FINAL_ACTION, ACTION_TS FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NOT NULL AND RECOMMENDED_ACTION IS NULL ORDER BY ACTION_TS DESC NULLS LAST",
        "narration": "Contract violations: a final action exists with no recommended action behind it."
    },
    {
        "skill": "action",
        "keywords": ["dispatch", "summary"],
        "sql": "SELECT COALESCE(FINAL_ACTION,'PENDING') AS OUTCOME, COUNT(*) AS CASE_COUNT, ROUND(AVG(RISK_SCORE),2) AS AVG_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY COALESCE(FINAL_ACTION,'PENDING') ORDER BY CASE_COUNT DESC",
        "narration": "Orchestrator dispatch summary by outcome."
    },
    {
        "skill": "action",
        "keywords": ["on", "call", "routing"],
        "sql": "SELECT a.CASE_ID, f.FACILITY_NAME, a.SEVERITY, a.RECOMMENDED_ACTION, p.NAME, p.ROLE, p.EMAIL, p.PHONE FROM GEOTECH.CORE.GEOTECH_AUDIT a JOIN GEOTECH.CORE.FACILITIES f ON a.FACILITY_ID = f.FACILITY_ID JOIN GEOTECH.CORE.PERSONNEL p ON a.FACILITY_ID = p.FACILITY_ID WHERE a.RECOMMENDED_ACTION IN ('URGENT_INSPECTION','EMERGENCY_ESCALATION') AND p.ON_CALL = TRUE ORDER BY a.SEVERITY, f.FACILITY_NAME",
        "narration": "On-call routing for urgent and emergency cases."
    },
    {
        "skill": "action",
        "keywords": ["acknowledgement", "sla"],
        "sql": "SELECT e.ESCALATION_ID, e.CASE_ID, f.FACILITY_NAME, e.SEVERITY, e.ESCALATION_TS, e.ACKNOWLEDGED, e.ACKNOWLEDGED_BY, e.ACKNOWLEDGED_TS, DATEDIFF('hour', e.ESCALATION_TS, COALESCE(e.ACKNOWLEDGED_TS, CURRENT_TIMESTAMP())) AS HOURS_TO_ACK FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e JOIN GEOTECH.CORE.FACILITIES f ON e.FACILITY_ID = f.FACILITY_ID ORDER BY HOURS_TO_ACK DESC",
        "narration": "Escalation acknowledgement latency, slowest first."
    },
    {
        "skill": "action",
        "keywords": ["notification", "channel"],
        "sql": "SELECT NOTIFICATION_CHANNEL, COUNT(*) AS ESCALATION_COUNT, SUM(CASE WHEN ACKNOWLEDGED THEN 1 ELSE 0 END) AS ACKNOWLEDGED_COUNT, ROUND(100.0*SUM(CASE WHEN ACKNOWLEDGED THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS ACK_RATE_PCT FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG GROUP BY NOTIFICATION_CHANNEL ORDER BY ESCALATION_COUNT DESC",
        "narration": "Notification channel effectiveness by acknowledgement rate."
    },
    {
        "skill": "action",
        "keywords": ["orchestrator", "inspection"],
        "sql": "SELECT i.INSPECTION_ID, f.FACILITY_NAME, i.INSPECTION_DATE, i.INSPECTOR_NAME, i.INSPECTION_TYPE, i.FOLLOW_UP_REQUIRED, i.FINDINGS FROM GEOTECH.CORE.INSPECTION_LOG i JOIN GEOTECH.CORE.FACILITIES f ON i.FACILITY_ID = f.FACILITY_ID WHERE i.INSPECTION_TYPE = 'TRIGGERED' AND i.FOLLOW_UP_REQUIRED = TRUE ORDER BY i.INSPECTION_DATE DESC",
        "narration": "Triggered inspections the orchestrator created with follow-up required."
    },
    {
        "skill": "action",
        "keywords": ["approval", "status"],
        "sql": "SELECT COALESCE(APPROVAL_STATUS,'NOT_SUBMITTED') AS APPROVAL_STATUS, COUNT(*) AS CASE_COUNT, ROUND(AVG(RISK_SCORE),2) AS AVG_RISK, COUNT(APPROVED_BY) AS WITH_APPROVER FROM GEOTECH.CORE.GEOTECH_AUDIT GROUP BY COALESCE(APPROVAL_STATUS,'NOT_SUBMITTED') ORDER BY CASE_COUNT DESC",
        "narration": "Human-in-the-loop approval pipeline state."
    },
    {
        "skill": "action",
        "keywords": ["executed", "engineer"],
        "sql": "SELECT ASSIGNED_ENGINEER, COUNT(*) AS EXECUTED_CASES, SUM(CASE WHEN FINAL_ACTION = 'EMERGENCY_ESCALATED' THEN 1 ELSE 0 END) AS EMERGENCIES, SUM(CASE WHEN FINAL_ACTION = 'URGENT_INSPECTION_DISPATCHED' THEN 1 ELSE 0 END) AS URGENT, ROUND(AVG(RISK_SCORE),2) AS AVG_RISK FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE ASSIGNED_ENGINEER IS NOT NULL AND FINAL_ACTION IS NOT NULL GROUP BY ASSIGNED_ENGINEER ORDER BY EXECUTED_CASES DESC",
        "narration": "Executed action load per assigned engineer."
    },
    {
        "skill": "action",
        "keywords": ["pipeline", "funnel"],
        "sql": "SELECT '1_DETECTED' AS STAGE, COUNT(*) AS CASE_COUNT FROM GEOTECH.CORE.GEOTECH_AUDIT UNION ALL SELECT '2_SYNTHESIZED', COUNT(*) FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE LLM_RATIONALE IS NOT NULL UNION ALL SELECT '3_RECOMMENDED', COUNT(*) FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE RECOMMENDED_ACTION IS NOT NULL UNION ALL SELECT '4_EXECUTED', COUNT(*) FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NOT NULL UNION ALL SELECT '5_ESCALATED', COUNT(*) FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG ORDER BY STAGE",
        "narration": "End-to-end pipeline funnel from detection through escalation."
    },
    {
        "skill": "action",
        "keywords": ["time", "to", "action"],
        "sql": "SELECT CASE_ID, SEVERITY, RISK_SCORE, DETECTED_TS, ACTION_TS, FINAL_ACTION, DATEDIFF('hour', DETECTED_TS, ACTION_TS) AS HOURS_TO_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE ACTION_TS IS NOT NULL ORDER BY HOURS_TO_ACTION DESC",
        "narration": "Detection-to-action latency per executed case."
    },
    {
        "skill": "action",
        "keywords": ["escalation", "severity"],
        "sql": "SELECT e.SEVERITY, COUNT(*) AS ESCALATIONS, SUM(CASE WHEN e.ACKNOWLEDGED THEN 1 ELSE 0 END) AS ACKNOWLEDGED, COUNT(DISTINCT e.FACILITY_ID) AS FACILITIES_AFFECTED FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e GROUP BY e.SEVERITY ORDER BY ESCALATIONS DESC",
        "narration": "Escalations grouped by severity with acknowledgement counts."
    },
    {
        "skill": "action",
        "keywords": ["escalation", "notes"],
        "sql": "SELECT e.ESCALATION_ID, e.CASE_ID, f.FACILITY_NAME, e.SEVERITY, e.ESCALATION_TS, e.ESCALATION_NOTES FROM GEOTECH.CORE.EMERGENCY_ESCALATION_LOG e JOIN GEOTECH.CORE.FACILITIES f ON e.FACILITY_ID = f.FACILITY_ID WHERE e.ESCALATION_NOTES IS NOT NULL ORDER BY e.ESCALATION_TS DESC",
        "narration": "Escalation notes recorded by the orchestrator."
    },
    {
        "skill": "action",
        "keywords": ["never", "actioned"],
        "sql": "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, SEVERITY, RISK_SCORE, DETECTED_TS, DATEDIFF('day', DETECTED_TS, CURRENT_TIMESTAMP()) AS DAYS_OPEN FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE FINAL_ACTION IS NULL ORDER BY DAYS_OPEN DESC, RISK_SCORE DESC",
        "narration": "Cases never actioned, oldest and highest risk first."
    },
]

# =============================================================================
# SKILL REGISTRY (display only)
# =============================================================================

SKILL_REGISTRY = {
    "drift": {
        "name": "$geotech-drift-scan",
        "desc": "Trend regression, rate-of-change, cross-sensor correlation",
        "keywords": ["drift", "trend", "slope", "regression", "rate of change", "anomaly", "deviation"]
    },
    "risk": {
        "name": "$geotech-risk-synthesis",
        "desc": "Risk reasoning scoped to flagged cases",
        "keywords": ["risk", "rationale", "why", "explain", "severity", "critical", "high", "synthesize"]
    },
    "action": {
        "name": "$geotech-action-orchestrator",
        "desc": "Deterministic action routing and dispatch",
        "keywords": ["action", "dispatch", "escalat", "inspect", "monitor", "assign", "engineer", "approve"]
    },
    "query": {
        "name": "$template-text-to-sql",
        "desc": "Template-based natural language to SQL",
        "keywords": []
    }
}


def detect_skills(question, template=None):
    """Build the execution trace. When the matched template declares a skill,
    that declaration wins over keyword guessing."""
    q = question.lower()
    triggered = []

    declared = template.get("skill") if template else None
    if declared and declared in SKILL_REGISTRY:
        triggered.append(SKILL_REGISTRY[declared])
    else:
        for key, skill in SKILL_REGISTRY.items():
            if key == "query":
                continue
            if any(kw in q for kw in skill["keywords"]):
                triggered.append(skill)

    triggered.append(SKILL_REGISTRY["query"])
    return triggered


def match_template(question):
    q = question.lower()
    best_match = None
    best_score = 0

    for template in TEMPLATES:
        keywords = template["keywords"]
        score = sum(1 for kw in keywords if kw in q)
        match_ratio = score / len(keywords) if keywords else 0

        if match_ratio > best_score and score >= 2:
            best_score = match_ratio
            best_match = template
        elif match_ratio == best_score and score > 0 and best_match:
            if score > sum(1 for kw in best_match["keywords"] if kw in q):
                best_match = template

    if best_match is None:
        for template in TEMPLATES:
            keywords = template["keywords"]
            if len(keywords) <= 2 and all(kw in q for kw in keywords):
                best_match = template
                break

    if best_match is None:
        for template in TEMPLATES:
            keywords = template["keywords"]
            if len(keywords) == 1 and keywords[0] in q:
                best_match = template
                break

    return best_match


def coerce_numeric(df):
    """Snowflake NUMBER(p,s) arrives as Decimal in object columns; convert to float
    so narration and chart logic can see them as numeric."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            converted = pd.to_numeric(out[col], errors="coerce")
            # Only accept the conversion if essentially every non-null value parsed
            non_null = out[col].notna().sum()
            if non_null > 0 and converted.notna().sum() == non_null:
                out[col] = converted.astype(float)
    return out


def generate_dynamic_narration(df, question, static_narration):
    """Generate natural language response from query results."""
    if df is None or df.empty:
        return "The query returned no results. Try rephrasing or checking if data exists for this filter."

    rows = len(df)
    cols = df.columns.tolist()

    # --- COUNT / HOW MANY queries (single value) ---
    if rows == 1 and len(cols) == 1:
        val = df.iloc[0, 0]
        col_name = cols[0].replace("_", " ").lower()
        return f"The {col_name} is **{val}**."

    # --- Single-row stats (AVG, MAX, MIN).
    #     Skipped when a skill-specific single-row shape below handles it better. ---
    SPECIFIC_SINGLE_ROW = ("PCT_FLAGGED", "PCT_COVERAGE", "ACK_RATE_PCT")
    if rows == 1 and len(cols) <= 5 and not any(c in cols for c in SPECIFIC_SINGLE_ROW):
        parts = []
        for col in cols:
            val = df.iloc[0][col]
            label = col.replace("_", " ").title()
            if isinstance(val, float) and val == int(val):
                val = int(val)
            parts.append(f"{label}: **{val}**")
        return " | ".join(parts)

    # --- GROUP BY with counts (severity, type, pattern distributions) ---
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    date_cols_found = [c for c in cols if 'DATE' in c.upper() or 'TS' in c.upper()]

    # --- $geotech-drift-scan result shapes ---
    if "PROJECTED_DAYS_TO_THRESHOLD" in cols and rows > 1:
        valid = df[df["PROJECTED_DAYS_TO_THRESHOLD"].notna()]
        if not valid.empty:
            top = valid.iloc[0]
            urgent = int((valid["PROJECTED_DAYS_TO_THRESHOLD"] < 30).sum())
            return (f"Soonest projected breach: **{top['SENSOR_ID']}** in "
                    f"**{int(top['PROJECTED_DAYS_TO_THRESHOLD'])}** days. "
                    f"{urgent} of {rows} extrapolated sensors are inside the 30-day window.")
        return f"{rows} sensors have a rising trend but none project a threshold breach."

    if "SLOPE_PER_DAY" in cols and rows > 1:
        top = df.iloc[0]
        rising = int((df["SLOPE_PER_DAY"] > 0).sum())
        falling = int((df["SLOPE_PER_DAY"] < 0).sum())
        resp = (f"Sensor **{top['SENSOR_ID']}** shows the steepest movement at "
                f"**{top['SLOPE_PER_DAY']}** per day")
        if "R_SQUARED" in cols:
            resp += f" (R-squared {top['R_SQUARED']})"
        resp += f". Of {rows} sensors, {rising} are rising and {falling} falling."
        if "R_SQUARED" in cols:
            strong = int((df["R_SQUARED"] > 0.5).sum())
            resp += f" {strong} have a statistically strong trend (R-squared > 0.5)."
        return resp

    if "SIGMA_ABOVE_MEAN" in cols and rows > 1:
        top = df.iloc[0]
        beyond3 = int((df["SIGMA_ABOVE_MEAN"] > 3).sum())
        return (f"Sensor **{top['SENSOR_ID']}** peaked **{top['SIGMA_ABOVE_MEAN']} sigma** above its "
                f"historical mean in the last 7 days. {beyond3} of {rows} sensors exceed 3 sigma.")

    if "SAME_DIRECTION_COUNT" in cols and rows > 1:
        top = df.iloc[0]
        multi = int((df["SAME_DIRECTION_COUNT"] > 1).sum())
        return (f"Strongest cross-sensor correlation: **{top['FACILITY_NAME']} / {top['ZONE']}** with "
                f"**{int(top['SAME_DIRECTION_COUNT'])}** of {int(top['SENSORS_IN_ZONE'])} sensors moving together. "
                f"{multi} of {rows} facility-zones show correlated movement.")

    if "MEAN_SHIFT" in cols and rows > 1:
        top = df.iloc[0]
        return (f"Largest baseline shift: **{top['SENSOR_ID']}** moved **{top['MEAN_SHIFT']}** "
                f"between its baseline mean ({top['BASELINE_MEAN']}) and recent 60-day mean "
                f"({top['RECENT_MEAN']}). Showing {rows} sensors.")

    if "MAX_7DAY_DELTA" in cols and rows > 1:
        top = df.iloc[0]
        return (f"Largest 7-day swing: **{top['SENSOR_ID']}** at **{top['MAX_7DAY_DELTA']}**. "
                f"Showing {rows} sensors ranked by rolling delta.")

    if "SCAN_ELIGIBILITY" in cols:
        eligible = int((df["SCAN_ELIGIBILITY"] == "ELIGIBLE").sum())
        return (f"**{eligible}** of {rows} sensors have the 60+ days of history the drift scan "
                f"requires; {rows - eligible} have insufficient history.")

    if "MISSING_14D" in cols and rows > 1:
        top = df.iloc[0]
        tot_missing = int(df["MISSING_14D"].sum())
        tot_suspect = int(df["SUSPECT_14D"].sum())
        return (f"{rows} sensors logged data-quality issues in the last 14 days: "
                f"**{tot_missing}** MISSING and **{tot_suspect}** SUSPECT readings. "
                f"Worst offender: **{top['SENSOR_ID']}**.")

    if "PCT_FLAGGED" in cols and rows == 1:
        r0 = df.iloc[0]
        return (f"Drift scan flagged **{int(r0['FLAGGED_SENSORS'])}** of "
                f"**{int(r0['TOTAL_SENSORS'])}** sensors (**{r0['PCT_FLAGGED']}%**); "
                f"{int(r0['CLEAN_SENSORS'])} are clean.")

    if "PCT_OF_THRESHOLD" in cols and rows > 1:
        top = df.iloc[0]
        over = int((df["PCT_OF_THRESHOLD"] >= 100).sum())
        near = int((df["PCT_OF_THRESHOLD"] >= 80).sum())
        resp = (f"**{top['SENSOR_ID']}** is at **{top['PCT_OF_THRESHOLD']}%** of its design threshold. "
                f"{near} of {rows} sensors are at 80% or above")
        resp += f", and {over} are at or past 100%." if over else "."
        return resp

    if "EXCEEDANCE_READINGS" in cols and rows > 1:
        top = df.iloc[0]
        total = int(df["EXCEEDANCE_READINGS"].sum())
        return (f"**{rows}** sensors have exceeded their design threshold, {total} readings in total. "
                f"Worst: **{top['SENSOR_ID']}** with {int(top['EXCEEDANCE_READINGS'])} exceedances "
                f"(peak {top['PEAK_VALUE']} vs threshold {top['DESIGN_THRESHOLD_VALUE']}).")

    if "DAYS_SINCE_LAST_READING" in cols and rows > 1:
        top = df.iloc[0]
        gap = top["DAYS_SINCE_LAST_READING"]
        if pd.isna(gap):
            return f"**{top['SENSOR_ID']}** has no readings at all. Showing {rows} sensors."
        if float(gap) < 1:
            return (f"No stale sensors — all {rows} shown reported within the last 24 hours "
                    f"(most recent gap {float(gap):g} days).")
        return (f"Most stale sensor: **{top['SENSOR_ID']}** — "
                f"**{int(gap)}** days since its last reading. Showing {rows} sensors.")

    if "SKILL_WEIGHT" in cols:
        top = df.iloc[0]
        return (f"Drift-scan pattern weights, highest first: **{top['PATTERN_TRIGGERED']}** "
                f"carries weight **{int(top['SKILL_WEIGHT'])}** and averages "
                f"{top['AVG_ACTUAL_RISK_SCORE']} actual risk across {int(top['CASE_COUNT'])} cases.")

    if "BAND_CHECK" in cols:
        matches = int((df["BAND_CHECK"] == "MATCH").sum())
        mismatches = rows - matches
        if mismatches == 0:
            return f"All {rows} cases have a severity consistent with the drift-scan risk bands."
        return (f"**{mismatches}** of {rows} cases have a severity that disagrees with the "
                f"risk-score band; {matches} match.")

    # --- $geotech-risk-synthesis result shapes ---
    if "MONTHS_SINCE_CALIBRATION" in cols:
        top = df.iloc[0]
        return (f"{rows} isolated sustained-trend case(s) sit on sensors calibrated over a year ago — "
                f"possible calibration drift. Worst: **{top['SENSOR_ID']}** at "
                f"**{int(top['MONTHS_SINCE_CALIBRATION'])}** months since calibration.")

    if "SKILL_MINIMUM_ACTION" in cols:
        emerg = int((df["SKILL_MINIMUM_ACTION"] == "EMERGENCY_ESCALATION").sum())
        return (f"{rows} cross-sensor case(s) at EXTREME/HIGH facilities. Per skill rules "
                f"**{emerg}** require EMERGENCY_ESCALATION (under 30 days to threshold) and "
                f"{rows - emerg} require at least URGENT_INSPECTION.")

    if "SKILL_EXPECTED_ACTION" in cols:
        agree = int((df["RECOMMENDED_ACTION"] == df["SKILL_EXPECTED_ACTION"]).sum())
        return (f"{rows} data-quality-gap case(s). **{agree}** were routed to the expected "
                f"SCHEDULE_INSPECTION; {rows - agree} deviated.")

    if "EXPECTED_DEFAULT" in cols:
        top = df.iloc[0]
        return (f"**{rows}** recommendation(s) deviate from the severity default. Example: "
                f"{top['CASE_ID']} is {top['SEVERITY']} (default {top['EXPECTED_DEFAULT']}) but was "
                f"set to **{top['RECOMMENDED_ACTION']}**.")

    if "SKILL_DEFAULT_ACTION" in cols:
        agree = int((df["RECOMMENDED_ACTION"] == df["SKILL_DEFAULT_ACTION"]).sum())
        return (f"Severity-to-action mapping across {rows} combinations; **{agree}** follow the "
                f"skill default exactly.")

    if "PCT_COVERAGE" in cols and rows == 1:
        r0 = df.iloc[0]
        return (f"Rationale coverage is **{r0['PCT_COVERAGE']}%** — "
                f"{int(r0['WITH_RATIONALE'])} of {int(r0['TOTAL_CASES'])} cases have one, "
                f"{int(r0['MISSING_RATIONALE'])} missing.")

    if "RATIONALE_CHARS" in cols and rows > 1:
        top = df.iloc[0]
        avg = round(float(df["RATIONALE_CHARS"].mean()))
        return (f"Longest rationale is {int(top['RATIONALE_CHARS'])} characters on case "
                f"**{top['CASE_ID']}**; average across {rows} cases is {avg}.")

    if "PENDING_SYNTHESIS" in cols and rows > 1:
        total = int(df["PENDING_SYNTHESIS"].sum())
        top = df.iloc[0]
        return (f"**{total}** case(s) await synthesis; the largest group is {top['SEVERITY']} "
                f"with {int(top['PENDING_SYNTHESIS'])}.")

    if "HOURS_SINCE_DETECTION" in cols and rows > 1:
        top = df.iloc[0]
        return (f"Oldest open detection: **{top['CASE_ID']}** at "
                f"**{int(top['HOURS_SINCE_DETECTION'])}** hours. Showing {rows} cases by age.")

    # --- $geotech-action-orchestrator result shapes ---
    if "EXPECTED_FINAL_ACTION" in cols:
        pending = int(df["STILL_PENDING"].sum())
        total = int(df["CASE_COUNT"].sum())
        parts = [f"**{r['RECOMMENDED_ACTION']}** to {r['EXPECTED_FINAL_ACTION']} ({int(r['CASE_COUNT'])})"
                 for _, r in df.iterrows()]
        return (f"Branch mapping over {total} recommended cases: " + ", ".join(parts) +
                (f". **{pending}** still pending execution." if pending else ". All executed."))

    if "OUTCOME" in cols and "CASE_COUNT" in cols:
        total = int(df["CASE_COUNT"].sum())
        parts = [f"**{r['OUTCOME']}** ({int(r['CASE_COUNT'])})" for _, r in df.iterrows()]
        pend = df[df["OUTCOME"] == "PENDING"]["CASE_COUNT"].sum()
        return (f"Dispatch summary over {total} cases: " + ", ".join(parts) +
                (f". {int(pend)} awaiting action." if pend else ". Nothing pending."))

    if "NOTIFY_LIST" in cols:
        top = df.iloc[0]
        return (f"{rows} emergency-escalation case(s). Highest priority: **{top['CASE_ID']}** at "
                f"{top['FACILITY_NAME']} ({top['RISK_CLASSIFICATION']}), notifying {top['NOTIFY_LIST']}.")

    if "HOURS_TO_ACK" in cols:
        unack = int((df["ACKNOWLEDGED"] == False).sum()) if "ACKNOWLEDGED" in cols else 0
        top = df.iloc[0]
        avg = round(float(df["HOURS_TO_ACK"].mean()), 1)
        resp = (f"{rows} escalation(s); slowest acknowledgement **{int(top['HOURS_TO_ACK'])}h** "
                f"(average {avg}h).")
        resp += f" **{unack}** still unacknowledged." if unack else " All acknowledged."
        return resp

    if "HOURS_TO_ACTION" in cols:
        top = df.iloc[0]
        avg = round(float(df["HOURS_TO_ACTION"].mean()), 1)
        return (f"Detection-to-action latency across {rows} executed cases averages **{avg}h**; "
                f"slowest was {top['CASE_ID']} at {int(top['HOURS_TO_ACTION'])}h.")

    if "ACK_RATE_PCT" in cols:
        top = df.iloc[0]
        return (f"{rows} notification channel(s). **{top['NOTIFICATION_CHANNEL']}** carried the most "
                f"({int(top['ESCALATION_COUNT'])}) with a {top['ACK_RATE_PCT']}% acknowledgement rate.")

    if "EXECUTED_CASES" in cols:
        top = df.iloc[0]
        total = int(df["EXECUTED_CASES"].sum())
        return (f"**{top['ASSIGNED_ENGINEER']}** carries the most executed actions "
                f"({int(top['EXECUTED_CASES'])} of {total}) across {rows} engineers.")

    if "STAGE" in cols and "CASE_COUNT" in cols:
        parts = [f"{r['STAGE'][2:].replace('_',' ').title()}: **{int(r['CASE_COUNT'])}**"
                 for _, r in df.iterrows()]
        return "Pipeline funnel — " + ", ".join(parts) + "."

    if "APPROVAL_STATUS" in cols and "CASE_COUNT" in cols:
        total = int(df["CASE_COUNT"].sum())
        parts = [f"**{r['APPROVAL_STATUS']}** ({int(r['CASE_COUNT'])})" for _, r in df.iterrows()]
        return f"Approval pipeline over {total} cases: " + ", ".join(parts) + "."

    if "DAYS_OPEN" in cols and rows > 1:
        top = df.iloc[0]
        return (f"**{rows}** case(s) have no final action. Oldest is {top['CASE_ID']} at "
                f"**{int(top['DAYS_OPEN'])}** days open (risk {top['RISK_SCORE']}).")

    if "DAYS_SINCE_CALIBRATION" in cols and rows > 1 and "SENSOR_ID" in cols:
        top = df.iloc[0]
        return (f"**{top['SENSOR_ID']}** ({top['SENSOR_TYPE']}) is most overdue at "
                f"**{int(top['DAYS_SINCE_CALIBRATION'])}** days since calibration. "
                f"{rows} sensors are past the 180-day mark.")

    # --- Time-series results (guarded: the date must be the leading dimension) ---

    # --- TOP N / ranked case lists (must run before the distribution branch,
    #     otherwise CASE_IDs get treated as categories and RISK_SCORE gets summed) ---
    if "RISK_SCORE" in cols and "CASE_ID" in cols and rows > 1:
        max_risk = df["RISK_SCORE"].max()
        min_risk = df["RISK_SCORE"].min()
        avg_risk = round(float(df["RISK_SCORE"].mean()), 2)

        response = f"Showing {rows} cases. Risk scores range from **{min_risk}** to **{max_risk}** (avg: {avg_risk})."

        if "SEVERITY" in cols:
            critical_count = int((df["SEVERITY"] == "CRITICAL").sum())
            high_count = int((df["SEVERITY"] == "HIGH").sum())
            sev_parts = []
            if critical_count:
                sev_parts.append(f"**{critical_count}** CRITICAL")
            if high_count:
                sev_parts.append(f"**{high_count}** HIGH")
            if sev_parts:
                response += f" Includes {' and '.join(sev_parts)}."

        if "ZONE" in cols and not df["ZONE"].isna().all():
            zone_counts = df["ZONE"].value_counts()
            response += f" Most affected zone: {zone_counts.index[0]} ({int(zone_counts.iloc[0])} cases)."

        if "DAYS_TO_THRESHOLD" in cols and not df["DAYS_TO_THRESHOLD"].isna().all():
            soonest = df["DAYS_TO_THRESHOLD"].min()
            response += f" Nearest threshold breach in **{soonest}** days."

        return response

    # --- Facility-related aggregates (before generic distribution) ---
    if "FACILITY_NAME" in cols and rows > 1:
        if "AVG_RISK_SCORE" in cols or "AVG_RISK" in cols:
            risk_col = "AVG_RISK_SCORE" if "AVG_RISK_SCORE" in cols else "AVG_RISK"
            top = df.iloc[0]
            overall = round(float(df[risk_col].mean()), 2)
            resp = (f"**{top['FACILITY_NAME']}** has the highest average risk at **{top[risk_col]}** "
                    f"across {rows} facilities (overall avg: {overall}).")
            if "CASE_COUNT" in cols:
                resp += f" It has {top['CASE_COUNT']} cases."
            return resp
        if "SENSOR_COUNT" in cols:
            top = df.iloc[0]
            total = int(df["SENSOR_COUNT"].sum())
            return (f"**{top['FACILITY_NAME']}** leads with {top['SENSOR_COUNT']} sensors. "
                    f"Total across {rows} facilities: {total}.")
        if "CASE_COUNT" in cols:
            top = df.iloc[0]
            total = int(df["CASE_COUNT"].sum())
            resp = f"**{top['FACILITY_NAME']}** has the most cases ({top['CASE_COUNT']}) of {total} total across {rows} facilities."
            if "CRITICAL" in cols:
                crit_total = int(df["CRITICAL"].sum())
                resp += f" {crit_total} are CRITICAL."
            return resp
        if "INSPECTION_COUNT" in cols:
            top = df.iloc[0]
            return f"**{top['FACILITY_NAME']}** has the most inspections ({top['INSPECTION_COUNT']}). Showing {rows} facilities."
        if "DAYS_SINCE_REVIEW" in cols:
            top = df.iloc[0]
            return (f"**{top['FACILITY_NAME']}** is longest overdue for review at "
                    f"**{top['DAYS_SINCE_REVIEW']}** days. Showing {rows} facilities.")

    # --- Genuine aggregate distribution: one category column + a count-like measure.
    #     A second numeric column is tolerated when it is a percentage of the first. ---
    AGG_HINTS = ("COUNT", "TOTAL", "NUM", "CASES", "READINGS", "ESCALATIONS")
    PCT_HINTS = ("PERCENTAGE", "PCT", "PERCENT", "SHARE")

    measure_col = next((c for c in num_cols if any(h in c.upper() for h in AGG_HINTS)), None)
    extra_nums = [c for c in num_cols if c != measure_col]
    extras_are_pct = all(any(h in c.upper() for h in PCT_HINTS) for c in extra_nums)

    is_distribution = (
        len(cat_cols) == 1
        and measure_col is not None
        and extras_are_pct
        and rows <= 12
    )

    if is_distribution:
        cat_col = cat_cols[0]
        num_col = measure_col
        total = float(df[num_col].sum())

        if total > 0:
            top_row = df.iloc[0]
            top_name = top_row[cat_col]
            top_val = float(top_row[num_col])
            top_pct = round(top_val * 100.0 / total, 1)

            def _fmt(v):
                f = float(v)
                return str(int(f)) if f == int(f) else f"{f:g}"

            summary_parts = [f"**{row[cat_col]}** ({_fmt(row[num_col])})" for _, row in df.iterrows()]
            breakdown = ", ".join(summary_parts[:5])
            if rows > 5:
                breakdown += f", and {rows - 5} more"

            insight = ""
            if top_pct > 50:
                insight = f" {top_name} dominates at {top_pct}% of the total."
            elif top_pct > 30:
                insight = f" {top_name} leads with {top_pct}% of total."

            label = num_col.replace("_", " ").lower()
            return f"Across {rows} groups there are {int(total)} {label}: {breakdown}.{insight}"

    # --- Ranked results with RISK_SCORE but no CASE_ID ---
    if "RISK_SCORE" in cols and rows > 1:
        max_risk = df["RISK_SCORE"].max()
        min_risk = df["RISK_SCORE"].min()
        avg_risk = round(float(df["RISK_SCORE"].mean()), 2)
        return f"Showing {rows} rows. Risk scores range from **{min_risk}** to **{max_risk}** (avg: {avg_risk})."

    # --- Zone aggregates ---
    if "ZONE" in cols and "AVG_RISK" in cols and rows > 1:
        top = df.iloc[0]
        resp = f"Zone **{top['ZONE']}** carries the highest average risk at **{top['AVG_RISK']}** across {rows} zones."
        if "CRITICAL_COUNT" in cols:
            resp += f" It has {top['CRITICAL_COUNT']} CRITICAL cases."
        return resp

    # --- Personnel results ---
    if "NAME" in cols:
        if "ACTIVE_CASES" in cols:
            top_person = df.iloc[0]["NAME"]
            top_cases = df.iloc[0]["ACTIVE_CASES"]
            return f"**{top_person}** has the highest workload with {top_cases} active cases. Showing {rows} engineers."
        if "ESCALATION_COUNT" in cols:
            top_person = df.iloc[0][cat_cols[0]] if cat_cols else df.iloc[0][cols[0]]
            top_count = df.iloc[0][num_cols[0]] if num_cols else "N/A"
            return f"**{top_person}** received the most escalations ({top_count}). Showing {rows} personnel."
        return f"Found {rows} personnel records."

    # --- Sensor results ---
    if "SENSOR_ID" in cols and rows > 1:
        if "DAYS_SINCE_CALIBRATION" in cols:
            worst = df.iloc[0]
            return f"**{worst['SENSOR_ID']}** ({worst['SENSOR_TYPE']}) is most overdue at {worst['DAYS_SINCE_CALIBRATION']} days since calibration. Found {rows} overdue sensors."
        if "CASE_COUNT" in cols:
            top = df.iloc[0]
            return f"Sensor **{top['SENSOR_ID']}** ({top['SENSOR_TYPE']}) has the most audit cases ({top['CASE_COUNT']}). Showing top {rows}."
        if "READING_COUNT" in cols:
            top = df.iloc[0]
            return f"Sensor **{top['SENSOR_ID']}** has the most readings ({top['READING_COUNT']}). Showing {rows} sensors."
        return f"Found {rows} sensors matching your query."

    date_cols_found = [c for c in cols if 'DATE' in c.upper() or 'TS' in c.upper()]
    is_series = (
        len(date_cols_found) == 1
        and date_cols_found[0] == cols[0]
        and len(num_cols) == 1
        and rows > 2
    )
    if is_series:
        measure = num_cols[0]
        first_val = df[measure].iloc[0]
        last_val = df[measure].iloc[-1]
        trend = "increasing" if last_val > first_val else "decreasing" if last_val < first_val else "stable"
        peak = df.loc[df[measure].idxmax()]
        return (f"Showing {rows} points over time; the trend is **{trend}** "
                f"(from {first_val} to {last_val}). Peak was {peak[measure]} on "
                f"{str(peak[cols[0]])[:10]}.")

    # --- Escalation results ---
    if "ESCALATION_ID" in cols or "ESCALATION_TS" in cols:
        if "ACKNOWLEDGED" in cols:
            unack = len(df[df["ACKNOWLEDGED"] == False])
            return f"Found {rows} escalations. **{unack}** are still unacknowledged."
        return f"Found {rows} escalation records."

    # --- Inspection results ---
    if "INSPECTION_ID" in cols:
        if "FOLLOW_UP_REQUIRED" in cols:
            fu_count = len(df[df["FOLLOW_UP_REQUIRED"] == True])
            return f"Found {rows} inspections. **{fu_count}** require follow-up action."
        return f"Found {rows} inspection records."

    # --- Escalation per engineer (NOTIFIED_PERSONNEL) ---
    if "NOTIFIED_PERSONNEL" in cols and num_cols:
        top = df.iloc[0]
        return f"**{top['NOTIFIED_PERSONNEL']}** received the most escalations ({top[num_cols[0]]}). Showing {rows} personnel."

    # --- Facility roster (name + dam engineering attributes) ---
    if "FACILITY_NAME" in cols and "DAM_TYPE" in cols and rows > 1:
        parts = [f"Showing {rows} facilities"]
        if "RISK_CLASSIFICATION" in cols:
            vc = df["RISK_CLASSIFICATION"].value_counts()
            parts.append("by class: " + ", ".join(f"**{k}** ({int(v)})" for k, v in vc.items()))
        if "DAM_HEIGHT_M" in cols and df["DAM_HEIGHT_M"].notna().any():
            tallest = df.loc[df["DAM_HEIGHT_M"].idxmax()]
            parts.append(f"tallest is **{tallest['FACILITY_NAME']}** at {tallest['DAM_HEIGHT_M']}m")
        if "AGE_YEARS" in cols and df["AGE_YEARS"].notna().any():
            oldest = df.loc[df["AGE_YEARS"].idxmax()]
            parts.append(f"oldest is **{oldest['FACILITY_NAME']}** at {int(oldest['AGE_YEARS'])} years")
        if "STORAGE_CAPACITY_MM3" in cols and df["STORAGE_CAPACITY_MM3"].notna().any():
            parts.append(f"combined storage {round(float(df['STORAGE_CAPACITY_MM3'].sum()), 1)} Mm3")
        return "; ".join(parts) + "."

    # --- Multi-measure time series (date leads, several measures) ---
    if date_cols_found and date_cols_found[0] == cols[0] and len(num_cols) >= 1 and rows > 1:
        measure = _pick_measure(num_cols, question)
        first_val, last_val = df[measure].iloc[0], df[measure].iloc[-1]
        trend = "increasing" if last_val > first_val else "decreasing" if last_val < first_val else "flat"
        peak = df.loc[df[measure].idxmax()]
        label = measure.replace("_", " ").lower()
        extra = ""
        others = [c for c in num_cols if c != measure]
        if others:
            extra = f" Total {others[0].replace('_',' ').lower()}: {int(df[others[0]].sum())}."
        return (f"Showing {rows} periods; {label} is **{trend}** "
                f"(from {first_val} to {last_val}), peaking at {peak[measure]} on "
                f"{str(peak[cols[0]])[:10]}.{extra}")

    # --- Generic fallback: summarise the leading dimension and measure ---
    if cat_cols and num_cols:
        cat_col = cat_cols[0]
        measure = _pick_measure(num_cols, question)
        total = float(df[measure].sum())
        top = df.loc[df[measure].idxmax()]
        label = measure.replace("_", " ").lower()

        def _n(v):
            f = float(v)
            return str(int(f)) if f == int(f) else f"{round(f, 2):g}"

        head = [f"**{r[cat_col]}** ({_n(r[measure])})" for _, r in df.head(4).iterrows()]
        more = f", and {rows - 4} more" if rows > 4 else ""
        lead = f"**{top[cat_col]}** leads on {label} with {_n(top[measure])}"
        return (f"{rows} rows grouped by {cat_col.replace('_',' ').lower()}: "
                f"{', '.join(head)}{more}. {lead} (total {_n(total)}).")

    if num_cols:
        measure = _pick_measure(num_cols, question)
        total = float(df[measure].sum())
        avg = round(float(df[measure].mean()), 2)
        label = measure.replace("_", " ").lower()
        return f"{rows} rows returned. {label.title()}: total {int(total)}, average {avg}."

    if cat_cols:
        lead = cat_cols[0]
        distinct = df[lead].nunique()
        return (f"{rows} records returned across {distinct} distinct "
                f"{lead.replace('_',' ').lower()} value(s); first is **{df.iloc[0][lead]}**.")

    return f"{rows} rows returned across {len(cols)} columns."


def extract_tables_from_sql(sql_text):
    pattern = r'GEOTECH\.CORE\.(\w+)'
    matches = re.findall(pattern, sql_text, re.IGNORECASE)
    return list(set(matches))


def _pick_measure(num_cols, question):
    """Pick the most relevant numeric column for charting based on the question."""
    if not num_cols:
        return None
    q = question.lower()

    # If the user asked about average/risk, prefer an AVG/RISK column over a COUNT column
    if any(w in q for w in ("average", "avg", "mean", "risk")):
        for c in num_cols:
            if "AVG" in c.upper() or "RISK" in c.upper():
                return c
    # If the user asked how many / count, prefer a count-like column
    if any(w in q for w in ("how many", "count", "number of", "total")):
        for c in num_cols:
            if any(h in c.upper() for h in ("COUNT", "TOTAL", "NUM")):
                return c
    return num_cols[0]


def detect_chart_type(df, question):
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    date_cols = [c for c in df.columns if 'TS' in c.upper() or 'DATE' in c.upper() or 'TIME' in c.upper()]

    if len(df) < 2:
        return None, None, None

    measure = _pick_measure(num_cols, question)
    if measure is None:
        return None, None, None

    if date_cols:
        return "line", date_cols[0], measure

    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    if cat_cols and len(df) <= 20:
        return "bar", cat_cols[0], measure

    if len(df) <= 20:
        return "bar", df.columns[0], measure

    return None, None, None


def render_execution_trace(skills, elapsed_ms):
    steps_html = ""
    for i, skill in enumerate(skills):
        icon = "&#9679;" if i < len(skills) - 1 else "&#9673;"
        connector = "<div style='width:2px; height:12px; background:#334155; margin-left:6px;'></div>" if i < len(skills) - 1 else ""
        steps_html += (
            f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:2px;'>"
            f"<span style='color:#6ee7b7; font-size:0.7rem;'>{icon}</span>"
            f"<code style='color:#29B5E8; font-size:0.75rem; background:#0f172a; padding:2px 6px; border-radius:4px;'>{skill['name']}</code>"
            f"<span style='color:#64748b; font-size:0.7rem;'>{skill['desc']}</span>"
            f"</div>{connector}"
        )
    return (
        f"<div style='background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:12px 14px; margin-bottom:12px;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
        f"<span style='color:#94a3b8; font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>Execution Trace</span>"
        f"<span style='color:#64748b; font-size:0.7rem;'>{elapsed_ms}ms</span>"
        f"</div>{steps_html}</div>"
    )


def render_citation(tables):
    if not tables:
        return ""
    badges = " ".join(
        f"<code style='background:#1e293b; color:#6ee7b7; padding:2px 8px; border-radius:4px; font-size:0.72rem;'>GEOTECH.CORE.{t}</code>"
        for t in tables
    )
    return (
        f"<div style='margin-top:8px; padding:8px 12px; background:#0f172a; border-radius:6px; border:1px solid #1e293b;'>"
        f"<span style='color:#94a3b8; font-size:0.7rem; font-weight:600; margin-right:8px;'>SOURCE:</span>{badges}</div>"
    )


def render():
    st.markdown("## GeoTech Agent")
    st.caption(f"Natural language queries over GEOTECH.CORE — {len(TEMPLATES)} pre-built SQL patterns")

    st.markdown("")
    st.markdown("")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if not st.session_state.chat_history:
        st.markdown(
            "<div style='text-align:center; padding:80px 0 60px 0; color:#64748b;'>"
            "<p style='font-size:1.1rem; margin-bottom:8px;'>Ask anything about your geotechnical data</p>"
            "<p style='font-size:0.8rem;'>"
            "\"Top 10 sensors by risk score\" &bull; "
            "\"Cases by severity count\" &bull; "
            "\"Average risk score per facility\" &bull; "
            "\"Escalations dispatched per engineer\"</p>"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        for entry in st.session_state.chat_history:
            st.markdown(f"**You:** {entry['question']}")
            st.markdown("")
            if entry.get("trace_html"):
                st.markdown(entry["trace_html"], unsafe_allow_html=True)
            if entry.get("narration"):
                st.markdown(entry["narration"])
            if entry.get("result") is not None:
                df = entry["result"]
                st.dataframe(df.reset_index(drop=True), use_container_width=True)
                chart_type = entry.get("chart_type")
                x_col = entry.get("chart_x")
                y_col = entry.get("chart_y")
                if chart_type and x_col and y_col:
                    try:
                        chart_df = df[[x_col, y_col]].copy()
                        if chart_type == "bar":
                            chart_df = chart_df.sort_values(y_col, ascending=False).reset_index(drop=True)
                            pad = len(str(len(chart_df)))
                            chart_df[x_col] = [f"{str(i+1).zfill(pad)}. {v}" for i, v in enumerate(chart_df[x_col])]
                        if any(k in y_col.upper() for k in ["SCORE", "RISK", "PCT", "PERCENT"]):
                            chart_df[y_col] = chart_df[y_col].clip(upper=100)
                        chart_df = chart_df.set_index(x_col)
                        if chart_type == "line":
                            st.line_chart(chart_df, use_container_width=True)
                        elif chart_type == "bar":
                            st.bar_chart(chart_df, use_container_width=True)
                    except Exception:
                        pass
            if entry.get("citation_html"):
                st.markdown(entry["citation_html"], unsafe_allow_html=True)
            with st.expander("View SQL"):
                st.code(entry["sql"], language="sql")
            st.markdown("---")

    spinner_placeholder = st.empty()

    st.markdown("")

    input_col, btn_col = st.columns([9, 1])
    with input_col:
        user_question = st.text_input(
            "message",
            placeholder="Enter a prompt...",
            label_visibility="collapsed",
            key="chat_input"
        )
    with btn_col:
        send_clicked = st.button("Send", use_container_width=True)

    if send_clicked and user_question:
        with spinner_placeholder:
            with st.spinner("Processing your request..."):
                start_time = time.time()
                generated_sql = ""
                try:
                    # Match template first so the trace can use its declared skill
                    template = match_template(user_question)
                    triggered_skills = detect_skills(user_question, template)

                    if template is None:
                        generated_sql = "SELECT CASE_ID, FACILITY_ID, SENSOR_ID, ZONE, SEVERITY, RISK_SCORE, PATTERN_TRIGGERED, RECOMMENDED_ACTION FROM GEOTECH.CORE.GEOTECH_AUDIT ORDER BY RISK_SCORE DESC LIMIT 15"
                        static_narration = f"I couldn't find an exact match for \"{user_question}\". Here are the top audit cases by risk score. Try asking about: severity counts, facility risk, sensor types, escalations, inspections, or personnel."
                    else:
                        generated_sql = template["sql"]
                        static_narration = template["narration"]

                    # Execute SQL on Snowflake
                    query_result = coerce_numeric(session.sql(generated_sql).to_pandas())

                    # Generate dynamic narration from results
                    narration = generate_dynamic_narration(query_result, user_question, static_narration)

                    # Extract source tables
                    source_tables = extract_tables_from_sql(generated_sql)
                    citation_html = render_citation(source_tables)

                    # Auto-detect chart
                    chart_type, chart_x, chart_y = None, None, None
                    if not query_result.empty:
                        chart_type, chart_x, chart_y = detect_chart_type(query_result, user_question)

                    elapsed_ms = int((time.time() - start_time) * 1000)
                    trace_html = render_execution_trace(triggered_skills, elapsed_ms)

                    st.session_state.chat_history.append({
                        "question": user_question,
                        "sql": generated_sql,
                        "result": query_result if not query_result.empty else None,
                        "narration": narration,
                        "trace_html": trace_html,
                        "citation_html": citation_html,
                        "chart_type": chart_type,
                        "chart_x": chart_x,
                        "chart_y": chart_y,
                        "error": None
                    })
                    _rerun()

                except Exception as e:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    trace_html = render_execution_trace(
                        detect_skills(user_question, match_template(user_question)), elapsed_ms
                    )
                    st.session_state.chat_history.append({
                        "question": user_question,
                        "sql": generated_sql if generated_sql else "-- No template matched",
                        "result": None,
                        "narration": f"Error: {str(e)[:200]}",
                        "trace_html": trace_html,
                        "citation_html": "",
                        "chart_type": None,
                        "chart_x": None,
                        "chart_y": None,
                        "error": str(e)
                    })
                    _rerun()

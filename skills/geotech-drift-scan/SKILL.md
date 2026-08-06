# Geotechnical Drift Scan

Deterministic detection only — no LLM judgment in this skill.

## When to invoke
"scan sensors", "run drift detection", "check geotechnical anomalies"

## Steps
1. For each sensor with ≥60 days of NORMAL/SUSPECT readings, compute:
   - Baseline mean/stddev from the window prior to the most recent 60 days
   - Rolling trend: linear regression slope + R² over the most recent 60 days
   - Rate-of-change: max 7-day rolling delta vs historical day-over-day stddev, in sigma
   - days_to_threshold: if R² > 0.5 and trend moves toward design_threshold_value,
     extrapolate the slope to estimate days until reaching it
   - data_quality: count of MISSING/SUSPECT readings in the last 14 days
2. Cross-sensor correlation (group-level, not per-sensor): within each facility+zone,
   count sensors trending the same direction in the same 60-day window, above a minimal
   slope magnitude
3. risk_score weights (sum, capped at 100):
   CROSS_SENSOR_CORRELATION=45, THRESHOLD_APPROACH(<30 days)=35,
   RATE_OF_CHANGE_SPIKE=30, SUSTAINED_TREND(isolated)=15, DATA_QUALITY_GAP=10
4. severity: CRITICAL ≥70, HIGH 50-69, MEDIUM 25-49, LOW <25
5. INSERT one row per flagged sensor/pattern into GEOTECH_AUDIT

## Output contract
Every row needs: case_id, facility_id, sensor_id, zone, detected_ts, pattern_triggered,
days_to_threshold, risk_score, severity. Leave llm_rationale/recommended_action/final_action null.
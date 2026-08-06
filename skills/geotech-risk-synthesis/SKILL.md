# Geotechnical Risk Synthesis

LLM reasoning, scoped strictly to flagged cases.

## When to invoke
"analyze flagged cases" or automatically after `$geotech-drift-scan` finds >0 flagged rows

## Steps
1. SELECT unresolved rows (llm_rationale IS NULL) from GEOTECH_AUDIT
2. JOIN in: facility risk_classification, sensor_type, zone, days_to_threshold, and any
   recent INSPECTION_LOG findings for that facility
3. Produce per case:
   - `llm_rationale`: plain engineering-language explanation (e.g. why correlated movement
     across multiple sensors in one zone is a structural signal, not sensor noise)
   - `recommended_action`: MONITOR / SCHEDULE_INSPECTION / URGENT_INSPECTION / EMERGENCY_ESCALATION
4. Guidance:
   - CROSS_SENSOR_CORRELATION at an EXTREME/HIGH facility → minimum URGENT_INSPECTION;
     EMERGENCY_ESCALATION if days_to_threshold < 30
   - days_to_threshold < 14 (any pattern) → EMERGENCY_ESCALATION regardless of facility class
   - Isolated SUSTAINED_TREND with no correlation, no threshold approach, and
     last_calibration_date > 12 months ago → lean SCHEDULE_INSPECTION, note "possible
     calibration drift" in the rationale
   - DATA_QUALITY_GAP alone → SCHEDULE_INSPECTION (check the sensor/logger, don't escalate)
   - Otherwise default by severity: LOW→MONITOR, MEDIUM→SCHEDULE_INSPECTION,
     HIGH→URGENT_INSPECTION, CRITICAL→EMERGENCY_ESCALATION
5. UPDATE GEOTECH_AUDIT with llm_rationale + recommended_action

## Output contract
Never modify final_action or action_ts. Every flagged row must get a rationale — don't
silently skip one.
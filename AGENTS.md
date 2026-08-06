# Geotechnical Sensor Drift Monitoring Agent

## Pipeline (strict order)
1. `$geotech-drift-scan` → writes new rows to GEOTECH.CORE.GEOTECH_AUDIT
   (pattern_triggered, risk_score, severity populated; llm_rationale/final_action null)
2. `$geotech-risk-synthesis` → reads unresolved rows, joins FACILITIES + INSPECTION_LOG,
   writes llm_rationale + recommended_action
3. `$geotech-action-orchestrator` → reads recommended_action, branches, writes
   final_action + action_ts, creates INSPECTION_LOG/EMERGENCY_ESCALATION_LOG entries

## Required roles
- `$geotech-drift-scan`: SELECT on SENSOR_READINGS, SENSORS; INSERT on GEOTECH_AUDIT
- `$geotech-risk-synthesis`: SELECT on GEOTECH_AUDIT, FACILITIES, INSPECTION_LOG; UPDATE on GEOTECH_AUDIT
- `$geotech-action-orchestrator`: UPDATE on GEOTECH_AUDIT; INSERT on INSPECTION_LOG, EMERGENCY_ESCALATION_LOG

## Rule: never skip a stage
Do not call `$geotech-action-orchestrator` on a case with no `llm_rationale`. This is
enforced by a PreToolUse hook (see .cortex/hooks/hooks.json) — do not rely on this
instruction alone. If a required grant is missing, halt and report exactly which grant
is needed.
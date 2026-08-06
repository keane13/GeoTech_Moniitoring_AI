# Geotechnical Action Orchestrator

Deterministic branching + real writes. Every branch must be auditable.

## When to invoke
"execute decisions", "process cases" or automatically after `$geotech-risk-synthesis` completes

## Steps
1. SELECT rows where recommended_action IS NOT NULL AND final_action IS NULL
2. Branch:
   - **MONITOR**: final_action='LOGGED_MONITORING', action_ts=now(), no other write
   - **SCHEDULE_INSPECTION**: INSERT into INSPECTION_LOG (inspection_type='TRIGGERED',
     follow_up_required=TRUE), assign the facility's SITE_GEOTECH_ENGINEER,
     final_action='INSPECTION_SCHEDULED'
   - **URGENT_INSPECTION**: same as above but notify DAM_SAFETY_ENGINEER_OF_RECORD,
     final_action='URGENT_INSPECTION_DISPATCHED'
   - **EMERGENCY_ESCALATION**: INSERT into EMERGENCY_ESCALATION_LOG (notified_personnel =
     DAM_SAFETY_ENGINEER_OF_RECORD + OPERATIONS_MANAGER for that facility), notify on-call,
     final_action='EMERGENCY_ESCALATED'
3. If a write fails (permission, lock, timeout): log the failure with case_id and error,
   leave final_action null for retry, report failed case_ids clearly — never continue silently
4. Idempotent: skip any case where final_action is already set
5. Print summary: N monitored, N scheduled, N urgent, N emergency-escalated, N failed

## Output contract
Never set final_action without a corresponding recommended_action. Never overwrite an
existing final_action.
#!/bin/bash
INPUT=$(cat)
SQL_TEXT=$(echo "$INPUT" | jq -r '.tool_input.command // .tool_input.query // empty')

if echo "$SQL_TEXT" | grep -qi "UPDATE GEOTECH.CORE.GEOTECH_AUDIT" && echo "$SQL_TEXT" | grep -qi "final_action"; then
  CASE_ID=$(echo "$SQL_TEXT" | grep -oP "case_id\s*=\s*'\K[^']+")
  RATIONALE=$(cortex sql exec --format=csv \
    "SELECT llm_rationale FROM GEOTECH.CORE.GEOTECH_AUDIT WHERE case_id='$CASE_ID'" | tail -n1)
  if [ -z "$RATIONALE" ] || [ "$RATIONALE" == "NULL" ]; then
    echo "{\"systemMessage\": \"Blocked: case $CASE_ID has no llm_rationale yet — run \$geotech-risk-synthesis first.\"}"
    exit 2
  fi
fi
exit 0
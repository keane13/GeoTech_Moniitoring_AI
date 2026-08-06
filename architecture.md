# Architecture — GeoTech Sentinel

## 1. Problem & Scope

Tailings storage facilities are monitored by hundreds of geotechnical sensors, but industry
practice is largely threshold-based: an alert fires only once a reading crosses a hard design
limit. Real incidents are typically preceded by gradual, correlated drift across multiple
sensors in the same zone — a pattern invisible to single-sensor threshold checks.

This system detects that leading-indicator pattern, reasons about its significance given
facility-specific context, and routes it to the right action automatically — from raw sensor
readings to a logged, notified decision, with minimal human intervention for routine cases.

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Snowflake (GEOTECH.CORE)                    │
│  FACILITIES · SENSORS · SENSOR_READINGS · INSPECTION_LOG ·     │
│  PERSONNEL · GEOTECH_AUDIT · EMERGENCY_ESCALATION_LOG          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   Cortex Code (CoCo)  │
                │     agent runtime     │
                └───────────┬───────────┘
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│  $geotech-    │  │ $geotech-risk-     │  │ $geotech-action-     │
│  drift-scan   │→ │ synthesis          │→ │ orchestrator          │
│(deterministic)│  │ (LLM, scoped)      │  │(deterministic branch) │
└───────────────┘  └────────────────────┘  └───────────┬──────────┘
                                                       │
                    ┌──────────────────────┬────────────┘
                    ▼                      ▼
             PreToolUse hook        PostToolUse hook
           (order enforcement)     (Slack fallback)
                    │                      │
                    ▼                      ▼
            Slack MCP tool         Streamlit Dashboard
           (primary alert)        (monitoring + audit)
```

## 3. Data Model

Six tables in `GEOTECH.CORE`:

| Table | Purpose |
|-------|---------|
| `FACILITIES` | Risk classification per facility |
| `SENSORS` | Type, zone, design threshold |
| `SENSOR_READINGS` | Time-series sensor data |
| `INSPECTION_LOG` | Inspection records and scheduling |
| `PERSONNEL` | Engineers for assignment/escalation |
| `GEOTECH_AUDIT` | Case ledger — flagged pattern, rationale, final action |
| `EMERGENCY_ESCALATION_LOG` | Highest-severity tier tracking |

## 4. Agent Skills — Responsibility Boundary

The pipeline deliberately separates *detection* and *routing* (cheap, deterministic, fully
auditable) from *judgment* (the one place an LLM call is actually justified):

- **`$geotech-drift-scan`** — pure SQL/statistics: rolling trend regression, rate-of-change vs
  historical baseline, cross-sensor correlation within a zone, threshold-approach forecasting.
  No LLM call. Runs against the full sensor fleet cheaply and reproducibly.

- **`$geotech-risk-synthesis`** — the only LLM-reasoning step, and it only ever sees the small
  set of already-flagged cases plus their joined context (facility risk class, inspection
  history). It explains *why* a statistical pattern matters in engineering terms and proposes
  an action tier.

- **`$geotech-action-orchestrator`** — deterministic branching on the proposed action tier,
  performs the actual writes (audit update, inspection scheduling, emergency log) and the
  external Slack notification for high-severity cases.

## 5. Governance Layer (Hooks)

Two hooks enforce rules that would otherwise live only as text in `AGENTS.md` — turning
"the agent should follow this order" into "the agent cannot violate this order":

- **`PreToolUse`** — blocks any write that sets `final_action` on a case whose
  `llm_rationale` is still null, forcing stage 2 to run before stage 3 regardless of how the
  agent is prompted.

- **`PostToolUse`** — a Slack-notification safety net (see section 6) that fires independently of
  whether the orchestrator's own MCP call succeeded, so a high-severity case is never silently
  unnotified.

## 6. External Integrations (MCP)

A Slack MCP server is registered in `mcp.json`. `$geotech-action-orchestrator` calls its
`slack_post_message`-equivalent tool directly as part of the `URGENT_INSPECTION` and
`EMERGENCY_ESCALATION` branches, formatting the alert from the case's own facility, zone,
severity, and rationale — this is the agent using an external tool as part of its reasoning,
not a static templated notification.

## 7. Streamlit Dashboard

A Streamlit in Snowflake (SiS) app provides operational monitoring with:

- **Overview** — system status and technology stack summary
- **Dashboard** — KPI cards, facility drill-down, sensor trend charts with threshold projection, zone correlation views
- **Audit Trail** — full traceability of flagged cases with LLM rationale and action history
- **Chatbot** — natural language queries over geotechnical data using Snowflake Cortex text-to-SQL

The dashboard is a presentation and monitoring layer — all detection, reasoning, and action
logic lives in the CoCo skills, not in the UI.

## 8. Design Tradeoffs

- **Deterministic-first over all-LLM**: keeps the expensive/variable LLM call scoped to <10%
  of sensors on a typical run, and keeps detection logic auditable by a dam safety engineer
  without needing to trust a model's math.

- **Two notification paths (MCP + hook fallback)**: intentional redundancy for the highest-
  stakes tier — MCP is the primary, contextual path; the hook is a blunt but reliable safety
  net that doesn't depend on the orchestrator's own tool call succeeding.

- **Synthetic data**: used for the hackathon demo; production would replace
  `SENSOR_READINGS` ingestion with a real telemetry pipeline, no other component changes.

## 9. Judging Criteria Mapping

| Criterion | Where It's Addressed |
|-----------|---------------------|
| Real-world relevance | Section 1 — leading-indicator framing, life-safety + regulatory stakes |
| Multi-step orchestration | Sections 2, 4 — three-skill pipeline with distinct responsibilities |
| Error handling / decision branches | Section 5 — PreToolUse blocks; orchestrator has 4 explicit branches + failure logging |
| Strong use of CoCo tools | Section 6 — Skills, Hooks, and MCP all used for a genuine purpose, not decoration |
| End-to-end completeness | Section 2 — data, detection, reasoning, action, notification, audit, in one run |

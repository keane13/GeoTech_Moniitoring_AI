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

┌─────────────────────────────────────────────────────────────────┐
│ Snowflake (GEOTECH.CORE) │
│ FACILITIES · SENSORS · SENSOR_READINGS · INSPECTION_LOG · │
│ PERSONNEL · GEOTECH_AUDIT · EMERGENCY_ESCALATION_LOG │
└───────────────────────────┬───────────────────────────────────────┘
│
▼
┌───────────────────────┐
│ Cortex Code (CoCo) │
│ agent runtime │
└───────────┬───────────┘
┌────────────────────┼────────────────────┐
▼ ▼ ▼
┌───────────────┐ ┌────────────────────┐ ┌──────────────────────┐
│ $geotech- │ │ $geotech-risk- │ │ $geotech-action- │
│ drift-scan │→│ synthesis │→│ orchestrator │
│ (deterministic)│ │ (LLM, scoped) │ │ (deterministic branch)│
└───────────────┘ └────────────────────┘ └───────────┬──────────┘
│
┌────────────────────────────┼──────────────┐
▼ ▼ │
PreToolUse hook PostToolUse hook │
(order enforcement) (Slack fallback) │
│ │
▼ ▼
Slack MCP tool Astro showcase UI
(primary alert) (chat + dashboard)


## 3. Data Model

Six tables in `GEOTECH.CORE`: `FACILITIES` (risk classification per facility),
`SENSORS` (type, zone, design threshold), `SENSOR_READINGS` (time-series), `INSPECTION_LOG`,
`PERSONNEL` (for assignment/escalation), `GEOTECH_AUDIT` (the case ledger — every flagged
pattern, its rationale, and its final action), and `EMERGENCY_ESCALATION_LOG` for the
highest-severity tier specifically.

## 4. Agent Skills — responsibility boundary

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

## 5. Governance layer (Hooks)

Two hooks enforce rules that would otherwise live only as text in `AGENTS.md` — turning
"the agent should follow this order" into "the agent cannot violate this order":

- **`PreToolUse`** — blocks any write that sets `final_action` on a case whose
  `llm_rationale` is still null, forcing stage 2 to run before stage 3 regardless of how the
  agent is prompted.
- **`PostToolUse`** — a Slack-notification safety net (see §6) that fires independently of
  whether the orchestrator's own MCP call succeeded, so a high-severity case is never silently
  unnotified.

## 6. External integrations (MCP)

A Slack MCP server is registered in `mcp.json`. `$geotech-action-orchestrator` calls its
`slack_post_message`-equivalent tool directly as part of the `URGENT_INSPECTION` and
`EMERGENCY_ESCALATION` branches, formatting the alert from the case's own facility, zone,
severity, and rationale — this is the agent using an external tool as part of its reasoning,
not a static templated notification.

## 7. Showcase UI

An Astro.js app (SSR mode) provides a demo-facing chat interface, bridging to the same CoCo
agent via the Cortex Code Agent SDK, plus a dashboard visualizing facility/zone status,
sensor trend charts, and the case audit trail. It is a presentation layer only — all
detection, reasoning, and action logic lives in the CoCo skills, not in the UI.

## 8. Design tradeoffs

- **Deterministic-first over all-LLM**: keeps the expensive/variable LLM call scoped to <10%
  of sensors on a typical run, and keeps detection logic auditable by a dam safety engineer
  without needing to trust a model's math.
- **Two notification paths (MCP + hook fallback)**: intentional redundancy for the highest-
  stakes tier — MCP is the primary, contextual path; the hook is a blunt but reliable safety
  net that doesn't depend on the orchestrator's own tool call succeeding.
- **Synthetic data**: used for the hackathon demo; production would replace
  `SENSOR_READINGS` ingestion with a real telemetry pipeline, no other component changes.

## 9. Judging criteria mapping

| Criterion | Where it's addressed |
|---|---|
| Real-world relevance | §1 — leading-indicator framing, life-safety + regulatory stakes |
| Multi-step orchestration | §2, §4 — three-skill pipeline with distinct responsibilities |
| Error handling / decision branches | §5 — PreToolUse blocks; orchestrator has 4 explicit branches + failure logging |
| Strong use of CoCo tools | §6 — Skills, Hooks, and MCP all used for a genuine purpose, not decoration |
| End-to-end completeness | §2 — data → detection → reasoning → action → notification → audit, in one run |
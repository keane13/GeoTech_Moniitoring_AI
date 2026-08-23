# GeoTech Sentinel — Predictive Tailings Dam Safety Agent

[![CoCo CLI](https://img.shields.io/badge/Snowflake-CoCo%20CLI-29B5E8?logo=snowflake)](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)
[![Hackathon](https://img.shields.io/badge/Hackathon-2026-orange)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Streamlit in Snowflake](https://img.shields.io/badge/Streamlit-in%20Snowflake-FF4B4B?logo=streamlit)](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
[![Unit Tests](https://img.shields.io/badge/Unit%20Tests-Passing-22c55e)]()

> Built for the **Snowflake CoCo CLI Hackathon 2026** — Intelligent Workflow Automation Agent track

An agentic AI system that continuously reasons over geotechnical sensor data to catch structural drift in tailings storage facilities **before** it becomes a threshold breach — turning a reactive safety process into a predictive one, fully orchestrated through Snowflake Cortex Code (CoCo) CLI.

---

![GeoTech Sentinel Dashboard](app_screenshot.png)

## Table of Contents

- [The Problem](#the-problem)
- [What It Does](#what-it-does)
- [Dashboard Features](#dashboard-features)
  - [Threshold & Scenario Simulator](#threshold--scenario-simulator)
  - [Human Feedback & Dispatch Panel](#human-feedback--dispatch-panel)
  - [Data Chatbot](#data-chatbot)
  - [Detection Diagnostics](#detection-diagnostics)
- [Design Principles](#design-principles)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Setup](#setup)
- [Running Locally](#running-locally)
- [Demo](#demo)
- [Impact](#impact)
- [Roadmap](#roadmap)
- [License](#license)

---

## The Problem

Mine tailings storage facilities are monitored by hundreds of sensors (piezometers, inclinometers, survey prisms, extensometers). Industry practice today is largely **threshold-based**: an alert only fires once a reading crosses a hard design limit — by which point structural movement is often already underway.

Catastrophic tailings dam failures were preceded by **gradual, statistically detectable drift** that never tripped a single threshold, because no system correlated multiple sensors across a zone in real time. The cost of missing this signal isn't just financial — it's life-safety, environmental, and regulatory.

**This project asks:** Can an AI agent catch that pattern early, reason about *why* it matters given the specific facility's risk context, and route it to the right human — automatically?

---

## What It Does

A three-stage agentic pipeline, orchestrated entirely through CoCo CLI, from raw sensor time-series to a routed, actionable safety decision — with no manual triage for the majority of cases.

`
Sensor readings (Snowflake)
         |
         v
+---------------------------+
|   $geotech-drift-scan   |  Deterministic: trend regression, rate-of-change,
|   (Agent Skill)           |  cross-sensor correlation, threshold-approach forecast
+-------------+-------------+
              |
              v
+---------------------------+
| $geotech-risk-synthesis |  LLM reasoning (scoped to flagged cases only):
|   (Agent Skill)           |  explains why it matters given facility risk class
+-------------+-------------+
              |
              v
+---------------------------+
| $geotech-action-         |  Deterministic branching: auto-monitor, schedule
|   orchestrator           |  inspection, or emergency escalation + Slack alert
+-------------+-------------+
              |
              v
       Human Review (Dispatch Panel)
              |
              v
Audit trail (Snowflake) + real-time Slack notification
`

A PreToolUse **hook** enforces the pipeline order at the tool-call level — the orchestrator cannot write a final decision for a case that hasn't been through risk synthesis, regardless of what the agent is asked to do.

---

## Dashboard Features

### Threshold & Scenario Simulator

Located in the **Dashboard** page, the Threshold & Scenario Simulator allows engineers to interactively model how a sensor will behave under different environmental stress conditions **before** a real event occurs.

**How it works:**

1. Select any sensor from the facility drill-down panel.
2. Adjust the **Alert Threshold** slider (±50% of the design threshold) to model what-if scenarios for threshold tightening or relaxation.
3. Choose a **stress scenario** from the dropdown:

| Scenario | Multiplier | Geotechnical Basis |
|----------|-----------|-------------------|
| Normal (current trend) | ×1.00 | Historical observed drift rate |
| Heavy Rainfall (+20% drift rate) | ×1.20 | Increased pore-water pressure accelerates consolidation |
| Seismic Event (+50% step spike) | ×1.50 | Sudden displacement event compresses timeline |
| Prolonged Drought (−30% reduced rate) | ×0.70 | Lower moisture reduces settlement rate |

**Output Metrics (5 metric cards):**

| Card | Description |
|------|-------------|
| **Sim. Threshold** | The adjusted alert threshold value (from slider) |
| **Drift Rate** | Simulated daily drift rate (units/day) under the selected scenario |
| **Est. Days to Breach** | Projected days until sensor value reaches the simulated threshold |
| **Risk Score** | Dynamic risk score (0–100) based on urgency and scenario severity |
| **Severity** | CRITICAL / HIGH / MEDIUM / LOW, derived from the simulated risk score |

**Risk Score logic mirrors the live pipeline:**
- Days to breach < 14 → +65 points (critical urgency)
- Days to breach 14–30 → +50 points (high urgency)
- Active drift detected → +15 points
- Seismic or extreme event → +10 points
- Capped at 100

A **180-day forecast chart** overlays the threshold line and historical 180-day window, so engineers can visually confirm the breach projection before acting.

---

### Human Feedback & Dispatch Panel

Located in the **Case Audit Trail** page, this is the **Human-in-the-Loop** component that sits between the AI recommendation and the final field action.

After $geotech-action-orchestrator generates a RECOMMENDED_ACTION, a human engineer reviews the AI rationale and either approves or rejects the dispatch. This implements a full **HITL (Human-in-the-Loop)** governance pattern.

**Workflow:**

`
AI recommends action
        |
        v
[Case Audit Trail — Dispatch Panel]
        |
        +-- Engineer reviews: LLM rationale, risk score, days to breach
        +-- Selects action: MONITOR / SCHEDULE_INSPECTION / URGENT_INSPECTION / EMERGENCY_ESCALATION
        +-- Assigns engineer from the facility's personnel roster
        |
        +-- Approve --> Writes FINAL_ACTION + APPROVED_BY + ACTION_TS to GEOTECH_AUDIT
        |               Creates INSPECTION_LOG entry (for inspection-type actions)
        |
        +-- Reject  --> Marks case REJECTED (awaits re-synthesis)
`

**Governance trail written per dispatch:**

| Field | Description |
|-------|-------------|
| FINAL_ACTION | The actual action taken |
| APPROVED_BY | The approving engineer's name |
| APPROVED_TS | Timestamp of approval |
| APPROVAL_STATUS | APPROVED or REJECTED |
| ASSIGNED_ENGINEER | Engineer dispatched to the site |

All writes are **idempotent** — re-running the orchestrator on an already-approved case will not overwrite the existing decision.

---

### Data Chatbot

The **Data Chatbot** page provides a natural language interface to the entire GEOTECH.CORE data warehouse, powered by an 80+ template SQL engine.

**How it works:**
1. User types a natural language question.
2. The engine scores keyword overlap between the query and the template library (organized by Skill domain: drift, isk, ction, query).
3. The best-matching SQL is executed on Snowflake.
4. Results are rendered as a data table with an auto-detected chart.
5. The **execution trace** shows which AI Skill was invoked for full pipeline transparency.

**Example queries for judges:**

| Query | What it returns |
|-------|----------------|
| show top highest risk score | Top 10 cases by risk score |
| show critical cases | All CRITICAL severity audit cases |
| what is action orchestrator | Explains Stage 3 with narration |
| how does drift scan work | Explains Stage 1 detection |
| what is risk synthesis | Explains LLM reasoning stage |
| drift scan risk weight | Pattern weights used by the detection engine |
| pipeline funnel | End-to-end case counts: detection → escalation |
| emergency escalation | Full escalation log with facility names |
| who is on call | Personnel currently on-call duty |

---

### Detection Diagnostics

The **Detection Diagnostics** page provides a statistical evaluation of the detection engine's performance against ground-truth labels in GEOTECH.CORE.GROUND_TRUTH_LABELS.

> **Note:** This is a diagnostic report for a deterministic (rule-based SQL) detection engine — metrics reflect **coverage** and **signal quality**, not ML model accuracy.

**Metrics displayed:** Precision · Recall · F1 Score · Accuracy · Confusion Matrix · Pattern Breakdown

---

## Design Principles

| Principle | How It's Applied |
|-----------|-----------------|
| **Deterministic where possible** | Detection (Stage 1) and action routing (Stage 3) are pure SQL/statistics — auditable, cheap, reproducible. LLM is invoked only where judgment is genuinely needed. |
| **Leading indicator, not lagging alarm** | Detection targets sustained trend + cross-sensor correlation + threshold-approach forecasting, not just breach detection. |
| **Governance is enforced, not documented** | The pipeline-order rule lives in a PreToolUse hook that can block a tool call. |
| **Every decision is traceable** | Every case carries its detection pattern, risk score, LLM rationale, and final action. |
| **Humans are in the loop where it matters** | The Dispatch Panel enforces human approval before any field action is committed. |
| **Simulator-driven safety planning** | The Threshold Simulator lets engineers model "what if heavy rainfall starts tomorrow?" before an event occurs. |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data warehouse | **Snowflake** — tables in GEOTECH.CORE |
| Agent runtime | **Cortex Code (CoCo) CLI** — 3 Agent Skills + 1 governance hook + Slack MCP |
| LLM | **Snowflake Cortex** (mistral-large2) |
| Operational dashboard | **Streamlit in Snowflake (SiS)** |
| Simulation engine | Python + pandas (geotechnical drift projection) |
| Testing | Python unittest (3 unit + integrity tests) |

---

## Repository Structure

`
.
├── AGENTS.md                        # Agent pipeline rules & governance
├── architecture.md                  # System architecture overview
├── README.md
│
├── cortex/
│   └── hooks/
│       ├── hooks.json               # PreToolUse pipeline-order hook
│       └── validate-geotech-pipeline.sh
│
├── skills/
│   ├── geotech-drift-scan/SKILL.md
│   ├── geotech-risk-synthesis/SKILL.md
│   └── geotech-action-orchestrator/SKILL.md
│
└── streamlit/
    ├── streamlit_app.py             # Navigation & routing
    ├── requirements.txt
    ├── test_integrity.py            # Unit + integrity tests (run: python test_integrity.py)
    ├── .streamlit/config.toml
    ├── components/
    │   └── styles.py                # CSS design system
    ├── utils/
    │   └── data.py                  # Snowpark session (dual-mode: SiS + local .env)
    └── views/
        ├── overview.py              # Project overview page
        ├── dashboard.py             # KPI dashboard + Threshold & Scenario Simulator
        ├── audit_trail.py           # Case audit + Human Dispatch (HITL) Panel
        ├── model_evaluation.py      # Detection Diagnostics page
        └── chatbot.py               # 80+ template NL chatbot with skill citation
`

---

## Setup

### 1. Snowflake — Schema & Data

Run in a Snowflake Worksheet:

`sql
CREATE DATABASE IF NOT EXISTS GEOTECH;
CREATE SCHEMA IF NOT EXISTS GEOTECH.CORE;
`

Then run prompts in a CoCo session to generate synthetic sensor data.

### 2. CoCo CLI — Run the Agentic Pipeline

`ash
cortex connections set <your_account>
cortex
`

Inside the CoCo session (run **in order** — the PreToolUse hook enforces this):

`
-drift-scan run for GEOTECH.CORE last 18 months
-risk-synthesis analyze flagged cases
-action-orchestrator execute decisions
`

### 3. Streamlit Dashboard — Deploy to Snowflake

`sql
CREATE STREAMLIT GEOTECH_DASHBOARD
  ROOT_LOCATION = '@GEOTECH.CORE.STREAMLIT_STAGE'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = COMPUTE_WH;
`

---

## Running Locally

### 1. Create .env file

`env
SNOWFLAKE_ACCOUNT=abc12345.us-central1.gcp
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=GEOTECH
SNOWFLAKE_SCHEMA=CORE
`

### 2. Install & Run

`ash
pip install snowflake-snowpark-python streamlit python-dotenv
cd streamlit
streamlit run streamlit_app.py
`

### 3. Run Unit Tests

`ash
python test_integrity.py
# Expected: Ran 3 tests in 0.001s — OK
`

---

## Impact

On a synthetic 240-sensor / 6-facility dataset modeled on real monitoring practice, this pipeline:

- Surfaces cross-sensor correlated drift **well before** a threshold breach triggers a conventional alarm
- Resolves the majority of flagged cases with no human triage required
- Provides a **scenario simulation tool** so safety engineers can proactively model rainfall, seismic, and drought conditions

---

## Roadmap

- Real sensor ingestion via Snowflake native connectors
- Subagent-based parallel case analysis for larger sensor fleets
- Two-way Slack (acknowledge/escalate from the alert thread)
- Integration with HDPE liner and water balance sensors

---

## License

MIT — see [LICENSE](LICENSE)

---

## Author

Built by **Simon Keane** — AI Engineer
> Built for the Snowflake CoCo CLI Hackathon 2026 — Freeport Indonesia Mine Safety

# Plan: Split streamlit_app.py into Modular Structure

## Target Structure
```
streamlit/
├── .streamlit/
│   └── config.toml          # Theme (already exists)
├── components/
│   ├── __init__.py           # Package marker
│   └── styles.py             # CSS injection + UI helper functions
├── utils/
│   ├── __init__.py           # Package marker
│   └── data.py              # Session init + all cached data loaders
├── pages/
│   ├── __init__.py           # Package marker
│   ├── dashboard.py          # Page 1: KPIs, facility drill-down, sensor detail, zone correlation
│   ├── audit_trail.py        # Page 2: Filters, table, LLM rationale
│   └── chatbot.py            # Page 3: Cortex AI text-to-SQL chatbot
├── streamlit_app.py          # Main entry: config, CSS, sidebar, page router
└── requirements.txt          # snowflake-snowpark-python, pandas, numpy
```

## SiS Compatibility Notes
- SiS supports importing from subdirectories if all files are uploaded to the stage
- Each subdirectory needs `__init__.py` for Python package imports to work
- Main entry point remains `streamlit_app.py` (referenced in CREATE STREAMLIT)
- All files must be PUT to `@GEOTECH.CORE.GEOTECH_DASHBOARD_STAGE/streamlit/` preserving paths

## Module Responsibilities

### `streamlit_app.py` (Entry Point)
- `st.set_page_config()`
- Import and apply CSS from `components.styles`
- Sidebar navigation (logo, radio, stats)
- Route to correct page module based on selection

### `components/styles.py`
- `inject_css()` → all custom CSS as a single function call
- `render_kpi_card(label, value, color)` → reusable KPI card HTML
- `render_zone_card(zone, sensor_count, severity, color)` → zone card HTML

### `utils/data.py`
- `get_session()` → cached `get_active_session()` wrapper
- `get_facilities()`, `get_sensors()`, `get_audit_cases()`, `get_escalations_30d()`
- `get_sensor_readings(sensor_id)`, `get_zone_readings(facility_id, zone)`

### `pages/dashboard.py`
- `render(session, facilities, sensors, audit_cases, escalations)` → all dashboard content

### `pages/audit_trail.py`
- `render(session, facilities, audit_cases)` → audit trail content

### `pages/chatbot.py`
- `render(session)` → chatbot content with Cortex AI

## Deployment
Upload each file maintaining directory structure:
```
PUT file://streamlit_app.py @stage/streamlit/
PUT file://components/__init__.py @stage/streamlit/components/
PUT file://components/styles.py @stage/streamlit/components/
PUT file://utils/__init__.py @stage/streamlit/utils/
PUT file://utils/data.py @stage/streamlit/utils/
PUT file://pages/__init__.py @stage/streamlit/pages/
PUT file://pages/dashboard.py @stage/streamlit/pages/
PUT file://pages/audit_trail.py @stage/streamlit/pages/
PUT file://pages/chatbot.py @stage/streamlit/pages/
```

import streamlit as st
import pandas as pd
import time
import re

from utils.data import session


SKILL_REGISTRY = {
    "drift": {
        "name": "$geotech-drift-scan",
        "desc": "Trend regression, rate-of-change, cross-sensor correlation",
        "keywords": ["drift", "trend", "slope", "regression", "rate of change", "anomaly", "deviation"]
    },
    "risk": {
        "name": "$geotech-risk-synthesis",
        "desc": "LLM risk reasoning scoped to flagged cases",
        "keywords": ["risk", "rationale", "why", "explain", "severity", "critical", "high", "synthesize", "assess"]
    },
    "action": {
        "name": "$geotech-action-orchestrator",
        "desc": "Deterministic action routing and dispatch",
        "keywords": ["action", "dispatch", "escalat", "inspect", "monitor", "assign", "engineer", "approve"]
    },
    "query": {
        "name": "cortex-text-to-sql",
        "desc": "Natural language to SQL via Cortex Complete",
        "keywords": []
    }
}


def detect_skills(question):
    q = question.lower()
    triggered = []
    for key, skill in SKILL_REGISTRY.items():
        if key == "query":
            continue
        if any(kw in q for kw in skill["keywords"]):
            triggered.append(skill)
    triggered.append(SKILL_REGISTRY["query"])
    return triggered


def extract_tables_from_sql(sql_text):
    pattern = r'GEOTECH\.CORE\.(\w+)'
    matches = re.findall(pattern, sql_text, re.IGNORECASE)
    return list(set(matches))


def detect_chart_type(df, question):
    q = question.lower()
    cols = [c.upper() for c in df.columns]
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    date_cols = [c for c in df.columns if 'TS' in c.upper() or 'DATE' in c.upper() or 'TIME' in c.upper()]

    if len(df) < 2:
        return None, None, None

    # Time series → line chart
    if date_cols and num_cols:
        return "line", date_cols[0], num_cols[0]

    # Categorical + numeric → bar chart
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    if cat_cols and num_cols and len(df) <= 20:
        return "bar", cat_cols[0], num_cols[0]

    # Multiple numeric columns → bar
    if len(num_cols) >= 1 and len(df) <= 20:
        label_col = df.columns[0]
        return "bar", label_col, num_cols[0]

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
    st.caption("AI-powered natural language queries over GEOTECH.CORE")

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
                # Auto chart
                chart_type = entry.get("chart_type")
                x_col = entry.get("chart_x")
                y_col = entry.get("chart_y")
                if chart_type and x_col and y_col:
                    try:
                        chart_df = df[[x_col, y_col]].copy()
                        # Sort by value descending for bar charts and prefix rank to preserve order
                        if chart_type == "bar":
                            chart_df = chart_df.sort_values(y_col, ascending=False).reset_index(drop=True)
                            pad = len(str(len(chart_df)))
                            chart_df[x_col] = [f"{str(i+1).zfill(pad)}. {v}" for i, v in enumerate(chart_df[x_col])]
                        # Cap score/percentage columns at 100
                        if any(k in y_col.upper() for k in ["SCORE", "RISK", "PCT", "PERCENT"]):
                            chart_df[y_col] = chart_df[y_col].clip(upper=100)
                        chart_df = chart_df.set_index(x_col)
                        if chart_type == "line":
                            st.line_chart(chart_df, use_container_width=True)
                        elif chart_type == "bar":
                            st.bar_chart(chart_df, use_container_width=True)
                    except Exception:
                        pass
            # Citation
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
                try:
                    triggered_skills = detect_skills(user_question)

                    escaped_prompt = user_question.replace("'", "''")

                    sql_gen_query = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mistral-large2',
                        CONCAT(
                            'You are a SQL expert for Snowflake. Generate a single SELECT query to answer the user question. ',
                            'Schema: GEOTECH.CORE. Tables: ',
                            'FACILITIES (facility_id STRING, facility_name, site_location, facility_type [TAILINGS_DAM/WASTE_ROCK_STORAGE/HEAP_LEACH], risk_classification [EXTREME/HIGH/SIGNIFICANT/LOW], construction_year, last_dam_safety_review_date). ',
                            'SENSORS (sensor_id STRING, facility_id, sensor_type [PIEZOMETER/INCLINOMETER/SURVEY_PRISM/EXTENSOMETER/SETTLEMENT_PLATE], zone [CREST_NORTH/CREST_SOUTH/DOWNSTREAM_SLOPE_EAST/DOWNSTREAM_SLOPE_WEST/TOE/FOUNDATION], install_date, design_threshold_value, design_threshold_unit, last_calibration_date). ',
                            'SENSOR_READINGS (reading_id, sensor_id, reading_ts TIMESTAMP, reading_value NUMBER, unit, data_quality_flag [NORMAL/SUSPECT/MISSING]). ',
                            'INSPECTION_LOG (inspection_id, facility_id, inspection_date, inspector_name, inspection_type [ROUTINE/TRIGGERED/INDEPENDENT_REVIEW], findings TEXT, follow_up_required BOOLEAN). ',
                            'PERSONNEL (engineer_id, name, role [SITE_GEOTECH_ENGINEER/DAM_SAFETY_ENGINEER_OF_RECORD/OPERATIONS_MANAGER], facility_id, on_call BOOLEAN). ',
                            'GEOTECH_AUDIT (case_id, facility_id, sensor_id, zone, detected_ts, pattern_triggered [SUSTAINED_TREND/RATE_OF_CHANGE_SPIKE/CROSS_SENSOR_CORRELATION/THRESHOLD_APPROACH/DATA_QUALITY_GAP], days_to_threshold NUMBER, risk_score NUMBER, severity [LOW/MEDIUM/HIGH/CRITICAL], llm_rationale TEXT, recommended_action, final_action [MONITOR/SCHEDULE_INSPECTION/URGENT_INSPECTION/EMERGENCY_ESCALATION], action_ts, assigned_engineer). ',
                            'EMERGENCY_ESCALATION_LOG (escalation_id, case_id, facility_id, escalation_ts, notified_personnel, protocol_reference, acknowledged BOOLEAN). ',
                            'IMPORTANT: Use fully qualified table names (GEOTECH.CORE.tablename). Return ONLY the raw SQL, no explanation, no markdown. ',
                            'User question: {escaped_prompt}'
                        )
                    ) AS generated_sql
                    """
                    result = session.sql(sql_gen_query).to_pandas()
                    generated_sql = result.iloc[0, 0].strip()

                    if generated_sql.startswith("```"):
                        lines = generated_sql.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        generated_sql = "\n".join(lines).strip()

                    query_result = session.sql(generated_sql).to_pandas()

                    # Extract source tables for citation
                    source_tables = extract_tables_from_sql(generated_sql)
                    citation_html = render_citation(source_tables)

                    # Auto-detect chart type
                    chart_type, chart_x, chart_y = None, None, None
                    if not query_result.empty:
                        chart_type, chart_x, chart_y = detect_chart_type(query_result, user_question)

                    # Generate narration
                    narration = ""
                    try:
                        narration_prompt = user_question.replace("'", "''")
                        if not query_result.empty:
                            result_preview = query_result.head(5).to_string(index=False)[:400].replace("'", "''").replace("\n", " | ")
                            narration_query = f"""
                            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                                'mistral-large2',
                                'User asked: "{narration_prompt}". Results: {result_preview}. Write a brief 1-2 sentence summary of these findings in natural language. Be concise, factual, no markdown.'
                            ) AS narration
                            """
                        else:
                            narration_query = f"""
                            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                                'mistral-large2',
                                'User asked: "{narration_prompt}". The query returned no results. Write a brief 1 sentence explaining why there might be no results and what the user could try instead. Be helpful, no markdown.'
                            ) AS narration
                            """
                        narration_result = session.sql(narration_query).to_pandas()
                        narration = narration_result.iloc[0, 0].strip()
                    except Exception:
                        narration = "Here are the results:" if not query_result.empty else "The query returned no matching data."

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
                    st.experimental_rerun()

                except Exception as e:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    trace_html = render_execution_trace(
                        detect_skills(user_question), elapsed_ms
                    )
                    st.session_state.chat_history.append({
                        "question": user_question,
                        "sql": generated_sql if 'generated_sql' in dir() else "Failed to generate query",
                        "result": None,
                        "narration": f"I encountered an issue processing your request: {str(e)[:200]}",
                        "trace_html": trace_html,
                        "citation_html": "",
                        "chart_type": None,
                        "chart_x": None,
                        "chart_y": None,
                        "error": str(e)
                    })
                    st.experimental_rerun()

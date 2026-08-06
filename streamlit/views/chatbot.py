import streamlit as st

from utils.data import session


def render():
    st.markdown("## GeoSense Agent")
    st.caption("AI-powered natural language queries over GEOTECH.CORE")

    st.markdown("")
    st.markdown("")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Message display area
    if not st.session_state.chat_history:
        st.markdown(
            "<div style='text-align:center; padding:80px 0 60px 0; color:#64748b;'>"
            "<p style='font-size:1.1rem; margin-bottom:8px;'>Ask anything about your geotechnical data</p>"
            "<p style='font-size:0.8rem;'>Examples: \"Which zones have correlated drift?\" &bull; "
            "\"Top sensors by risk score\" &bull; \"Show all emergency escalations\"</p>"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        for entry in st.session_state.chat_history:
            st.markdown(f"**You:** {entry['question']}")
            st.markdown("")
            if entry.get("narration"):
                st.markdown(entry["narration"])
            if entry.get("result") is not None:
                st.dataframe(entry["result"].reset_index(drop=True), use_container_width=True)
            with st.expander("View SQL"):
                st.code(entry["sql"], language="sql")
            st.markdown("---")

    # Spinner placeholder (above input)
    spinner_placeholder = st.empty()

    st.markdown("")

    # Input box - no form border
    input_col, btn_col = st.columns([9, 1])
    with input_col:
        user_question = st.text_input(
            "message",
            placeholder="Enter a prompt...",
            label_visibility="collapsed",
            key="chat_input"
        )
    with btn_col:
        send_clicked = st.button("➤", use_container_width=True)

    if send_clicked and user_question:
        with spinner_placeholder:
            with st.spinner("Processing your request..."):
                try:
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

                    # Generate natural language narration
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
                    except:
                        narration = "Here are the results:" if not query_result.empty else "The query returned no matching data."

                    st.session_state.chat_history.append({
                        "question": user_question,
                        "sql": generated_sql,
                        "result": query_result if not query_result.empty else None,
                        "narration": narration,
                        "error": None
                    })
                    st.experimental_rerun()

                except Exception as e:
                    st.session_state.chat_history.append({
                        "question": user_question,
                        "sql": generated_sql if 'generated_sql' in dir() else "Failed to generate query",
                        "result": None,
                        "narration": f"I encountered an issue processing your request: {str(e)[:200]}",
                        "error": str(e)
                    })
                    st.experimental_rerun()

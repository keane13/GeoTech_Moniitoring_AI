import streamlit as st


def render():
    st.markdown("## GeoTech Monitoring AI")
    st.markdown(
        "<p style='color:#94a3b8; font-size:1rem; margin-top:-8px;'>"
        "Predictive Tailings Dam Safety Monitoring System</p>",
        unsafe_allow_html=True
    )

    st.markdown("")

    # --- About ---
    st.markdown(
        "<div style='background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin-bottom:24px;'>"
        "<h4 style='margin:0 0 12px 0; color:#29B5E8;'>About</h4>"
        "<p style='color:#cbd5e1; margin:0; line-height:1.7;'>"
        "GeoTech Monitoring AI is an AI-powered geotechnical monitoring platform designed for "
        "tailings dam safety at Freeport Indonesia mining operations. It combines real-time "
        "sensor data with agentic AI pipelines to detect drift patterns, assess risk, and "
        "orchestrate emergency responses, enabling engineers to act before failures occur."
        "</p></div>",
        unsafe_allow_html=True
    )

    # --- Features ---
    st.markdown(
        "<div style='background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin-bottom:24px;'>"
        "<h4 style='margin:0 0 16px 0; color:#29B5E8;'>Features</h4>"
        "<div style='display:grid; grid-template-columns:1fr 1fr; gap:16px;'>"
        "  <div style='padding:12px; background:#0f172a; border-radius:8px;'>"
        "    <p style='margin:0 0 4px 0; color:#f1f5f9; font-weight:600;'>Real-time Dashboard</p>"
        "    <p style='margin:0; color:#94a3b8; font-size:0.85rem;'>KPI monitoring, facility drill-down, sensor trend charts with threshold projection</p>"
        "  </div>"
        "  <div style='padding:12px; background:#0f172a; border-radius:8px;'>"
        "    <p style='margin:0 0 4px 0; color:#f1f5f9; font-weight:600;'>Case Audit Trail</p>"
        "    <p style='margin:0; color:#94a3b8; font-size:0.85rem;'>Full traceability of flagged cases with LLM-generated risk rationale and action history</p>"
        "  </div>"
        "  <div style='padding:12px; background:#0f172a; border-radius:8px;'>"
        "    <p style='margin:0 0 4px 0; color:#f1f5f9; font-weight:600;'>AI Chatbot</p>"
        "    <p style='margin:0; color:#94a3b8; font-size:0.85rem;'>Natural language queries over geotechnical data using Snowflake Cortex text-to-SQL</p>"
        "  </div>"
        "  <div style='padding:12px; background:#0f172a; border-radius:8px;'>"
        "    <p style='margin:0 0 4px 0; color:#f1f5f9; font-weight:600;'>3-Stage Agentic Pipeline</p>"
        "    <p style='margin:0; color:#94a3b8; font-size:0.85rem;'>Drift Scan → Risk Synthesis → Action Orchestrator with governance hooks</p>"
        "  </div>"
        "</div></div>",
        unsafe_allow_html=True
    )

    # --- Data ---
    col1, col2 = st.columns(2)

    data_items = [
        ("FACILITIES", "6 mine-site facilities", "#29B5E8"),
        ("SENSORS", "240 monitoring sensors", "#22c55e"),
        ("SENSOR_READINGS", "18 months daily readings", "#a855f7"),
        ("GEOTECH_AUDIT", "AI-flagged risk cases", "#ef4444"),
        ("INSPECTION_LOG", "40 inspection records", "#f97316"),
        ("PERSONNEL", "12 engineers", "#eab308"),
        ("EMERGENCY_ESCALATION_LOG", "Escalation tracking", "#ec4899"),
    ]

    with col1:
        rows_html = ""
        for name, desc, accent in data_items:
            rows_html += (
                f"<div style='display:flex; align-items:center; padding:10px 14px; "
                f"background:#0f172a; border-radius:8px; margin-bottom:8px;'>"
                f"<div style='width:4px; height:32px; background:{accent}; border-radius:2px; margin-right:12px;'></div>"
                f"<div>"
                f"<p style='margin:0; color:#f1f5f9; font-size:0.85rem; font-weight:600;'>{name}</p>"
                f"<p style='margin:2px 0 0 0; color:#94a3b8; font-size:0.75rem;'>{desc}</p>"
                f"</div></div>"
            )
        st.markdown(
            f"<div style='background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px;'>"
            f"<h4 style='margin:0 0 16px 0; color:#29B5E8;'>Data</h4>"
            f"{rows_html}</div>",
            unsafe_allow_html=True
        )

    tech_items = [
        ("Platform", "Snowflake", "#29B5E8"),
        ("Frontend", "Streamlit in Snowflake (SiS)", "#22c55e"),
        ("AI Model", "Snowflake Cortex (mistral-large2)", "#a855f7"),
        ("Agent Framework", "Cortex Code (CoCo) CLI", "#f97316"),
        ("Compute", "Snowpark + Warehouse", "#eab308"),
        ("Governance", "PreToolUse hooks", "#ec4899"),
        ("Language", "Python 3.11 + SQL", "#64748b"),
    ]

    with col2:
        rows_html = ""
        for label, value, accent in tech_items:
            rows_html += (
                f"<div style='display:flex; align-items:center; padding:10px 14px; "
                f"background:#0f172a; border-radius:8px; margin-bottom:8px;'>"
                f"<div style='width:4px; height:32px; background:{accent}; border-radius:2px; margin-right:12px;'></div>"
                f"<div>"
                f"<p style='margin:0; color:#f1f5f9; font-size:0.85rem; font-weight:600;'>{label}</p>"
                f"<p style='margin:2px 0 0 0; color:#94a3b8; font-size:0.75rem;'>{value}</p>"
                f"</div></div>"
            )
        st.markdown(
            f"<div style='background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px;'>"
            f"<h4 style='margin:0 0 16px 0; color:#29B5E8;'>Technology Stack</h4>"
            f"{rows_html}</div>",
            unsafe_allow_html=True
        )

    st.markdown("")
    st.markdown(
        "<p style='text-align:center; color:#64748b; font-size:0.8rem; margin-top:24px;'>"
        "Built for Snowflake CoCo CLI Hackathon 2026 — Freeport Indonesia Mine Safety</p>",
        unsafe_allow_html=True
    )

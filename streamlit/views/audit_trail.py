import streamlit as st

from utils.data import approve_and_dispatch, reject_case, get_personnel


def render(facilities, audit_cases):
    st.markdown("## Case Audit Trail")
    st.caption("All flagged cases with filtering and full LLM rationale")

    st.markdown("")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_facility = st.multiselect("Facility", facilities["FACILITY_ID"].tolist(), default=[])
    with col_f2:
        filter_severity = st.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=[])
    with col_f3:
        filter_pattern = st.multiselect("Pattern", audit_cases["PATTERN_TRIGGERED"].unique().tolist(), default=[])
    with col_f4:
        filter_action = st.multiselect("Action", audit_cases["FINAL_ACTION"].dropna().unique().tolist(), default=[])

    filtered = audit_cases.copy()
    if filter_facility:
        filtered = filtered[filtered["FACILITY_ID"].isin(filter_facility)]
    if filter_severity:
        filtered = filtered[filtered["SEVERITY"].isin(filter_severity)]
    if filter_pattern:
        filtered = filtered[filtered["PATTERN_TRIGGERED"].isin(filter_pattern)]
    if filter_action:
        filtered = filtered[filtered["FINAL_ACTION"].isin(filter_action)]

    display_cols = ["CASE_ID", "FACILITY_ID", "SENSOR_ID", "ZONE", "PATTERN_TRIGGERED",
                    "SEVERITY", "RISK_SCORE", "DAYS_TO_THRESHOLD", "FINAL_ACTION", "ASSIGNED_ENGINEER"]
    st.dataframe(filtered[display_cols].reset_index(drop=True), use_container_width=True)

    st.markdown("")
    st.markdown("### LLM Rationale Details")

    severity_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}

    if not filtered.empty:
        for _, case in filtered.iterrows():
            sev = case["SEVERITY"]
            sev_col = severity_color.get(sev, "#64748b")
            pattern_label = case["PATTERN_TRIGGERED"].replace("_", " ").title()

            with st.expander(f"{case['CASE_ID']}  —  {case['SENSOR_ID']}  |  {pattern_label}  ({sev})"):
                # Severity badge + case metadata
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:12px; margin-bottom:16px;'>"
                    f"<span style='background:{sev_col}20; color:{sev_col}; padding:4px 12px; "
                    f"border-radius:20px; font-size:0.75rem; font-weight:700; border:1px solid {sev_col};'>{sev}</span>"
                    f"<span style='color:#94a3b8; font-size:0.8rem;'>{case['ZONE'].replace('_',' ').title()}</span>"
                    f"<span style='color:#64748b; font-size:0.8rem;'>|</span>"
                    f"<span style='color:#94a3b8; font-size:0.8rem;'>{case['FACILITY_ID']}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Metrics row
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.markdown(
                    f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
                    f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Risk Score</p>"
                    f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.3rem; font-weight:700;'>{case['RISK_SCORE']}</p>"
                    f"</div>", unsafe_allow_html=True
                )
                col_b.markdown(
                    f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
                    f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Days to Threshold</p>"
                    f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.3rem; font-weight:700;'>"
                    f"{case.get('DAYS_TO_THRESHOLD', 'N/A')}</p></div>", unsafe_allow_html=True
                )
                col_c.markdown(
                    f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
                    f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Final Action</p>"
                    f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.3rem; font-weight:700;'>"
                    f"{str(case.get('FINAL_ACTION', 'Pending')).replace('_',' ').title()}</p></div>", unsafe_allow_html=True
                )
                col_d.markdown(
                    f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
                    f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Engineer</p>"
                    f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.3rem; font-weight:700;'>"
                    f"{case.get('ASSIGNED_ENGINEER', '—')}</p></div>", unsafe_allow_html=True
                )

                st.markdown("")

                # LLM Rationale
                rationale = case.get("LLM_RATIONALE", None)
                if rationale and str(rationale) != "None":
                    st.markdown(
                        f"<div style='background:#0f172a; border-left:3px solid #29B5E8; border-radius:6px; "
                        f"padding:14px 16px; margin-top:8px;'>"
                        f"<p style='margin:0 0 6px 0; color:#29B5E8; font-size:0.75rem; font-weight:600; "
                        f"text-transform:uppercase; letter-spacing:0.05em;'>AI Rationale</p>"
                        f"<p style='margin:0; color:#cbd5e1; font-size:0.85rem; line-height:1.6;'>{rationale}</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.info("No LLM rationale available — run risk synthesis pipeline first.")

                # --- Human-in-the-Loop Action Buttons ---
                approval_status = case.get("APPROVAL_STATUS", None)
                recommended = case.get("RECOMMENDED_ACTION", None)

                if approval_status == "APPROVED":
                    st.markdown(
                        f"<div style='background:#065f4620; border:1px solid #065f46; border-radius:8px; padding:10px 14px; margin-top:12px;'>"
                        f"<span style='color:#6ee7b7; font-weight:600;'>Approved</span>"
                        f"<span style='color:#94a3b8; font-size:0.8rem; margin-left:12px;'>"
                        f"by {case.get('APPROVED_BY', '—')} at {str(case.get('APPROVED_TS', ''))[:19]}</span></div>",
                        unsafe_allow_html=True
                    )
                elif approval_status == "REJECTED":
                    st.markdown(
                        f"<div style='background:#7f1d1d20; border:1px solid #7f1d1d; border-radius:8px; padding:10px 14px; margin-top:12px;'>"
                        f"<span style='color:#fca5a5; font-weight:600;'>Rejected</span>"
                        f"<span style='color:#94a3b8; font-size:0.8rem; margin-left:12px;'>"
                        f"by {case.get('APPROVED_BY', '—')} at {str(case.get('APPROVED_TS', ''))[:19]}</span></div>",
                        unsafe_allow_html=True
                    )
                elif recommended and str(recommended) != "None":
                    st.markdown("")
                    st.markdown(
                        f"<div style='background:#1e293b; border:1px solid #334155; border-radius:8px; padding:14px; margin-top:8px;'>"
                        f"<p style='margin:0 0 8px 0; color:#fbbf24; font-size:0.75rem; font-weight:600; "
                        f"text-transform:uppercase; letter-spacing:0.05em;'>Pending Approval</p>"
                        f"<p style='margin:0; color:#f1f5f9; font-size:0.9rem;'>Recommended: "
                        f"<strong>{str(recommended).replace('_', ' ').title()}</strong></p></div>",
                        unsafe_allow_html=True
                    )

                    personnel = get_personnel()
                    engineer_options = personnel["NAME"].tolist()
                    case_key = case["CASE_ID"]

                    col_eng, col_approve, col_reject = st.columns([3, 1, 1])
                    with col_eng:
                        selected_engineer = st.selectbox(
                            "Assign Engineer",
                            engineer_options,
                            key=f"eng_{case_key}",
                            label_visibility="collapsed"
                        )
                    with col_approve:
                        if st.button("Approve & Dispatch", key=f"approve_{case_key}", type="primary"):
                            approve_and_dispatch(case_key, selected_engineer, recommended, selected_engineer)
                            st.success(f"Dispatched to {selected_engineer}")
                            st.experimental_rerun()
                    with col_reject:
                        if st.button("Reject", key=f"reject_{case_key}"):
                            reject_case(case_key, selected_engineer)
                            st.warning("Case rejected")
                            st.experimental_rerun()

    else:
        st.info("No cases match the current filters.")

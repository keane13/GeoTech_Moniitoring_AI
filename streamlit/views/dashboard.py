import streamlit as st
import pandas as pd
import numpy as np

from components.styles import render_kpi_card, render_zone_card
from utils.data import get_sensor_readings, get_zone_readings


def render(facilities, sensors, audit_cases, escalations):
    st.markdown("## GeoSense Monitoring Dashboard")
    st.caption("Predictive Tailings Dam Safety Monitoring — Real-time Operational View")

    # --- Year Filter ---
    years = sorted(
        pd.to_datetime(audit_cases["DETECTED_TS"]).dt.year.dropna().unique().tolist(),
        reverse=True
    ) if "DETECTED_TS" in audit_cases.columns and not audit_cases.empty else []

    if years:
        selected_year = st.selectbox("Filter Year", ["All"] + [str(y) for y in years], index=0, key="dash_year")
        if selected_year != "All":
            yr = int(selected_year)
            audit_cases = audit_cases[pd.to_datetime(audit_cases["DETECTED_TS"]).dt.year == yr]
            if "ESCALATION_TS" in escalations.columns:
                escalations = escalations[pd.to_datetime(escalations["ESCALATION_TS"]).dt.year == yr]

    # --- KPI Cards ---
    open_cases = audit_cases[audit_cases["FINAL_ACTION"] != "MONITOR"] if "FINAL_ACTION" in audit_cases.columns else audit_cases
    severity_counts = open_cases["SEVERITY"].value_counts().to_dict() if not open_cases.empty else {}

    kpis = [
        ("Facilities", len(facilities), "#29B5E8"),
        ("Sensors", len(sensors), "#29B5E8"),
        ("Critical", severity_counts.get("CRITICAL", 0), "#ef4444"),
        ("High", severity_counts.get("HIGH", 0), "#f97316"),
        ("Medium", severity_counts.get("MEDIUM", 0), "#eab308"),
        ("Escalations", len(escalations), "#a855f7"),
    ]

    kpi_cols = st.columns(6)
    for i, (label, value, color) in enumerate(kpis):
        with kpi_cols[i]:
            st.markdown(render_kpi_card(label, value, color), unsafe_allow_html=True)

    st.markdown("")

    # --- Facility Drill-Down ---
    st.markdown("### Facility Overview")

    facility_options = dict(zip(
        facilities["FACILITY_ID"] + " — " + facilities["FACILITY_NAME"],
        facilities["FACILITY_ID"]
    ))
    selected_facility_label = st.selectbox("Select Facility", list(facility_options.keys()), label_visibility="collapsed")
    selected_facility = facility_options[selected_facility_label]

    facility_sensors = sensors[sensors["FACILITY_ID"] == selected_facility]
    facility_zones = sorted(facility_sensors["ZONE"].unique())
    facility_audit = audit_cases[audit_cases["FACILITY_ID"] == selected_facility]

    severity_priority = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    status_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e", "NONE": "#64748b"}

    row1 = st.columns(3)
    row2 = st.columns(3)
    zone_containers = row1 + row2

    for i, zone in enumerate(facility_zones):
        if i >= 6:
            break
        zone_audit = facility_audit[facility_audit["ZONE"] == zone]
        zone_sensor_count = len(facility_sensors[facility_sensors["ZONE"] == zone])

        if not zone_audit.empty:
            worst = zone_audit.loc[zone_audit["SEVERITY"].map(lambda x: severity_priority.get(x, 0)).idxmax(), "SEVERITY"]
        else:
            worst = "NONE"

        color = status_color.get(worst, "#64748b")

        with zone_containers[i]:
            st.markdown(render_zone_card(zone, zone_sensor_count, worst, color), unsafe_allow_html=True)
            if not zone_audit.empty:
                for _, row in zone_audit.iterrows():
                    sev_color = status_color.get(row["SEVERITY"], "#64748b")
                    st.markdown(
                        f"<span style='color:{sev_color}; font-size:0.75rem; font-weight:600;'>"
                        f"{row['SEVERITY']}</span> "
                        f"<code style='font-size:0.75rem;'>{row['SENSOR_ID']}</code> "
                        f"<span style='color:#94a3b8; font-size:0.75rem;'>"
                        f"{row['PATTERN_TRIGGERED'].replace('_',' ').title()}</span>",
                        unsafe_allow_html=True
                    )

    st.markdown("")

    # --- Sensor Detail View ---
    st.markdown("### Sensor Detail")

    sensor_options = sorted(sensors["SENSOR_ID"].unique())
    selected_sensor = st.selectbox("Select Sensor", sensor_options)

    sensor_info = sensors[sensors["SENSOR_ID"] == selected_sensor].iloc[0]
    threshold = float(sensor_info["DESIGN_THRESHOLD_VALUE"])
    sensor_type = sensor_info["SENSOR_TYPE"]
    sensor_unit = sensor_info["DESIGN_THRESHOLD_UNIT"]

    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    col_info1.markdown(f"**Type**<br><span style='color:#94a3b8'>{sensor_type}</span>", unsafe_allow_html=True)
    col_info2.markdown(f"**Threshold**<br><span style='color:#94a3b8'>{threshold} {sensor_unit}</span>", unsafe_allow_html=True)
    col_info3.markdown(f"**Zone**<br><span style='color:#94a3b8'>{sensor_info['ZONE']}</span>", unsafe_allow_html=True)
    col_info4.markdown(f"**Facility**<br><span style='color:#94a3b8'>{sensor_info['FACILITY_ID']}</span>", unsafe_allow_html=True)

    readings = get_sensor_readings(selected_sensor)

    if not readings.empty:
        readings["READING_TS"] = pd.to_datetime(readings["READING_TS"])
        readings = readings.sort_values("READING_TS")

        readings["DAY_NUM"] = (readings["READING_TS"] - readings["READING_TS"].min()).dt.days
        if len(readings) > 2:
            z = np.polyfit(readings["DAY_NUM"].values, readings["READING_VALUE"].values.astype(float), 1)
            readings["TREND"] = z[0] * readings["DAY_NUM"] + z[1]
            slope_per_day = z[0]
        else:
            readings["TREND"] = readings["READING_VALUE"]
            slope_per_day = 0

        sensor_audit = audit_cases[audit_cases["SENSOR_ID"] == selected_sensor]
        days_to_thresh = None
        if not sensor_audit.empty:
            dtt = sensor_audit.iloc[0].get("DAYS_TO_THRESHOLD")
            if pd.notna(dtt):
                days_to_thresh = int(dtt)

        chart_data = readings[["READING_TS", "READING_VALUE", "TREND"]].copy()
        chart_data["THRESHOLD"] = threshold
        chart_data = chart_data.set_index("READING_TS")

        st.line_chart(chart_data, use_container_width=True)

        if days_to_thresh:
            st.warning(f"Estimated **{days_to_thresh} days** to threshold breach at current rate.")
        if slope_per_day != 0:
            direction = "rising" if slope_per_day > 0 else "falling"
            st.caption(f"Trend: {direction} at {abs(slope_per_day):.4f} {sensor_unit}/day")
    else:
        st.info("No readings available for this sensor.")

    st.markdown("")

    # --- Zone Correlation View ---
    st.markdown("### Zone Correlation")

    correlated_cases = audit_cases[audit_cases["PATTERN_TRIGGERED"] == "CROSS_SENSOR_CORRELATION"]

    if correlated_cases.empty:
        st.info("No active cross-sensor correlation flags.")
    else:
        corr_zones = correlated_cases[["FACILITY_ID", "ZONE"]].drop_duplicates()
        for _, row in corr_zones.iterrows():
            fac_id = row["FACILITY_ID"]
            zone_name = row["ZONE"]
            fac_name = facilities[facilities["FACILITY_ID"] == fac_id]["FACILITY_NAME"].values[0]

            st.markdown(f"**{fac_name}** — {zone_name.replace('_', ' ').title()}")

            zone_data = get_zone_readings(fac_id, zone_name)
            if not zone_data.empty:
                zone_data["READING_TS"] = pd.to_datetime(zone_data["READING_TS"])
                pivot = zone_data.pivot_table(
                    index="READING_TS", columns="SENSOR_ID", values="READING_VALUE", aggfunc="mean"
                )
                st.line_chart(pivot, use_container_width=True)

                flagged_sensors = correlated_cases[
                    (correlated_cases["FACILITY_ID"] == fac_id) & (correlated_cases["ZONE"] == zone_name)
                ]["SENSOR_ID"].tolist()
                st.caption(f"Flagged: {', '.join(flagged_sensors)}")
            else:
                st.info("No recent readings for this zone.")

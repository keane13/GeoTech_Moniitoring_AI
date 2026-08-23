import streamlit as st
import pandas as pd
import numpy as np

from components.styles import render_kpi_card, render_zone_card
from utils.data import get_sensor_readings, get_zone_readings


def render(facilities, sensors, audit_cases, escalations):
    st.markdown("## GeoTech Monitoring Dashboard")
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

        # --- Threshold Adjustment & Simulation Panel ---
        st.markdown("")
        st.markdown("#### Threshold & Scenario Simulation")
        st.caption("Adjust the alert threshold and apply geotechnical stress scenarios to project sensor breach timing.")

        last_value = float(readings["READING_VALUE"].iloc[-1])
        # Reference drift: use observed slope if meaningful, else use 1-year-to-threshold as baseline
        MIN_MEANINGFUL_SLOPE = 1e-6
        obs_slope_abs = abs(slope_per_day) if abs(slope_per_day) > MIN_MEANINGFUL_SLOPE else None

        sim_col1, sim_col2 = st.columns(2)

        with sim_col1:
            adjusted_threshold = st.slider(
                "Adjust Alert Threshold",
                min_value=float(threshold * 0.5),
                max_value=float(threshold * 1.5),
                value=float(threshold),
                step=float(max(threshold * 0.01, 0.001)),
                format="%.3f",
                key=f"thresh_{selected_sensor}"
            )

        with sim_col2:
            scenario = st.selectbox(
                "Simulate Scenario",
                ["Normal (current trend)", "Heavy Rainfall (+20% drift rate)", "Seismic Event (+50% step spike)", "Prolonged Drought (−30% reduced rate)"],
                key=f"scenario_{selected_sensor}"
            )

        # --- Compute gap and reference rate ---
        gap_to_threshold = adjusted_threshold - last_value  # signed: positive = sensor below threshold

        # Reference daily rate: use observed slope direction toward threshold,
        # fallback to gap/365 so the scenario always produces a visible number.
        if obs_slope_abs is not None:
            ref_rate = obs_slope_abs  # units/day from historical regression
        else:
            ref_rate = abs(gap_to_threshold) / 365.0  # baseline: 1 year to breach

        # --- Scenario multipliers (geotechnically grounded) ---
        # Heavy Rainfall: 20% faster consolidation/pore-pressure build-up → ×1.20
        # Seismic Event: 50% step-spike in displacement/pore-pressure → ×1.50
        # Prolonged Drought: 30% slower settlement due to lower moisture → ×0.70
        scenario_multiplier = {
            "Normal (current trend)": 1.00,
            "Heavy Rainfall (+20% drift rate)": 1.20,
            "Seismic Event (+50% step spike)": 1.50,
            "Prolonged Drought (−30% reduced rate)": 0.70,
        }[scenario]

        sim_rate = ref_rate * scenario_multiplier  # units/day toward threshold

        # Direction: always project toward the threshold
        if gap_to_threshold >= 0:
            sim_slope = sim_rate   # sensor below threshold → positive drift needed
        else:
            sim_slope = -sim_rate  # sensor already above threshold → negative drift

        # --- Days to breach ---
        sim_days_to_threshold = None
        sim_days_label = None

        if abs(gap_to_threshold) < 1e-9:
            sim_days_label = "Already at threshold"
        elif gap_to_threshold < 0:
            # sensor already above threshold
            sim_days_label = "Already breached"
        elif sim_rate < MIN_MEANINGFUL_SLOPE:
            sim_days_label = "Stable (no trend)"
        else:
            raw_days = abs(gap_to_threshold) / sim_rate
            if raw_days > 3650:
                sim_days_to_threshold = 3650
                sim_days_label = f"> 10 years"
            else:
                sim_days_to_threshold = raw_days
                years = int(raw_days // 365)
                months = int((raw_days % 365) // 30)
                if years > 0:
                    sim_days_label = f"{int(raw_days)} days (~{years}y {months}m)"
                elif months > 0:
                    sim_days_label = f"{int(raw_days)} days (~{months} mo)"
                else:
                    sim_days_label = f"{int(raw_days)} days"

        # --- Risk score (mirrors drift-scan pipeline logic) ---
        sim_risk_score = 0
        if sim_days_to_threshold is not None:
            if sim_days_to_threshold <= 14:
                sim_risk_score += 65   # <2 weeks: critical urgency
            elif sim_days_to_threshold <= 30:
                sim_risk_score += 50   # <1 month: high urgency
            elif sim_days_to_threshold <= 90:
                sim_risk_score += 30   # <3 months: elevated
            else:
                sim_risk_score += 10   # longer-term risk
        if sim_rate > MIN_MEANINGFUL_SLOPE:
            sim_risk_score += 15  # active drift bonus
        if scenario_multiplier >= 1.5:
            sim_risk_score += 10  # extreme event bonus

        sim_risk_score = min(sim_risk_score, 100)  # cap at 100

        if sim_risk_score >= 70:
            sim_severity = "CRITICAL"
            sev_color = "#ef4444"
        elif sim_risk_score >= 50:
            sim_severity = "HIGH"
            sev_color = "#f97316"
        elif sim_risk_score >= 25:
            sim_severity = "MEDIUM"
            sev_color = "#eab308"
        else:
            sim_severity = "LOW"
            sev_color = "#22c55e"

        # --- Display simulation results ---
        sim_r1, sim_r2, sim_r3, sim_r4, sim_r5 = st.columns(5)
        sim_r1.markdown(
            f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
            f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Sim. Threshold</p>"
            f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.0rem; font-weight:700;'>{adjusted_threshold:.3f} {sensor_unit}</p>"
            f"</div>", unsafe_allow_html=True
        )
        sim_r2.markdown(
            f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
            f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Drift Rate</p>"
            f"<p style='margin:4px 0 0 0; color:#38bdf8; font-size:1.0rem; font-weight:700;'>{sim_rate:.5f}</p>"
            f"<p style='margin:2px 0 0 0; color:#64748b; font-size:0.65rem;'>{sensor_unit}/day</p>"
            f"</div>", unsafe_allow_html=True
        )
        sim_r3.markdown(
            f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
            f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Est. Days to Breach</p>"
            f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:0.9rem; font-weight:700;'>"
            f"{sim_days_label}</p>"
            f"</div>", unsafe_allow_html=True
        )
        sim_r4.markdown(
            f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
            f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Risk Score</p>"
            f"<p style='margin:4px 0 0 0; color:#f1f5f9; font-size:1.0rem; font-weight:700;'>{sim_risk_score} / 100</p>"
            f"</div>", unsafe_allow_html=True
        )
        sim_r5.markdown(
            f"<div style='background:#0f172a; border-radius:8px; padding:12px; text-align:center;'>"
            f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase;'>Severity</p>"
            f"<p style='margin:4px 0 0 0; color:{sev_color}; font-size:1.0rem; font-weight:700;'>{sim_severity}</p>"
            f"</div>", unsafe_allow_html=True
        )

        # Simulated chart with adjusted threshold — always show to reflect scenario changes
        sim_chart = readings[["READING_TS", "READING_VALUE"]].copy()
        forecast_days = 180  # show 6-month horizon for better context
        future_ts = pd.date_range(readings["READING_TS"].max() + pd.Timedelta(days=1), periods=forecast_days, freq="D")

        # Forecast starts from the last actual reading and projects forward using simulated slope
        future_values = [last_value + sim_slope * (d + 1) for d in range(forecast_days)]

        forecast_df = pd.DataFrame({
            "READING_TS": future_ts,
            "READING_VALUE": [None] * forecast_days,
            "FORECAST": future_values
        })
        sim_chart["FORECAST"] = None
        sim_chart = pd.concat([sim_chart, forecast_df], ignore_index=True)
        sim_chart["SIM_THRESHOLD"] = adjusted_threshold

        # Only show last 180 days of readings + forecast for better visual contrast
        cutoff_ts = readings["READING_TS"].max() - pd.Timedelta(days=180)
        sim_chart["READING_TS_PARSED"] = pd.to_datetime(sim_chart["READING_TS"])
        sim_chart = sim_chart[sim_chart["READING_TS_PARSED"] >= cutoff_ts].drop(columns=["READING_TS_PARSED"])
        sim_chart = sim_chart.set_index("READING_TS")

        st.line_chart(sim_chart[["READING_VALUE", "FORECAST", "SIM_THRESHOLD"]], use_container_width=True)
        st.caption(
            f"Scenario: **{scenario}** · Drift rate: {sim_rate:.5f} {sensor_unit}/day · "
            f"Multiplier: ×{scenario_multiplier:.2f} · Est. breach: {sim_days_label}"
        )

    else:
        st.info("No readings available for this sensor.")

    st.markdown("")

    # --- Zone Correlation View ---
    st.markdown("### Zone Correlation")
    st.caption("% deviation from each sensor's own 30-day baseline — parallel movement indicates structural response")

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

                # Calculate % deviation from each sensor's own baseline (first 30 readings)
                def pct_from_baseline(group):
                    baseline = group["READING_VALUE"].iloc[:30].mean()
                    if baseline == 0:
                        baseline = 1
                    group["PCT_DEVIATION"] = ((group["READING_VALUE"] - baseline) / baseline) * 100
                    return group

                zone_data = zone_data.sort_values(["SENSOR_ID", "READING_TS"])
                zone_data = zone_data.groupby("SENSOR_ID", group_keys=False).apply(pct_from_baseline)

                pivot = zone_data.pivot_table(
                    index="READING_TS", columns="SENSOR_ID", values="PCT_DEVIATION", aggfunc="mean"
                )
                st.line_chart(pivot, use_container_width=True)

                flagged_sensors = correlated_cases[
                    (correlated_cases["FACILITY_ID"] == fac_id) & (correlated_cases["ZONE"] == zone_name)
                ]["SENSOR_ID"].tolist()
                st.caption(f"Flagged sensors: {', '.join(flagged_sensors)} | Y-axis: % deviation from individual baseline")
            else:
                st.info("No recent readings for this zone.")

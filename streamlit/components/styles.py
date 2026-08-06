import streamlit as st


def inject_css():
    st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.main .block-container {
    padding-top: 1rem !important;
}

[data-testid="stSidebar"] {
    min-width: 210px;
    max-width: 230px;
    background: linear-gradient(180deg, #0a0f1a 0%, #0c1929 40%, #11304a 100%) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem;
    background: transparent !important;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 0px !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
    padding: 12px 16px !important;
    margin: 4px 0 !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: background 0.2s !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(41, 181, 232, 0.1) !important;
}
[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] {
    background: rgba(41, 181, 232, 0.15) !important;
    border-left: 3px solid #29B5E8 !important;
}

div[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 18px;
}
div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


def render_kpi_card(label, value, color):
    return (
        f"<div style='background:#1e293b; border:1px solid #334155; border-radius:12px; "
        f"padding:20px 16px; text-align:center;'>"
        f"<p style='margin:0; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; "
        f"letter-spacing:0.05em;'>{label}</p>"
        f"<p style='margin:6px 0 0 0; color:{color}; font-size:2rem; font-weight:700; "
        f"line-height:1;'>{value}</p>"
        f"</div>"
    )


def render_zone_card(zone, sensor_count, severity, color):
    return (
        f"<div style='border-left:4px solid {color}; padding:12px 16px; "
        f"background:#1a2332; border-radius:8px; margin-bottom:8px;'>"
        f"<strong style='font-size:0.95rem;'>{zone.replace('_', ' ').title()}</strong><br>"
        f"<span style='color:#94a3b8; font-size:0.8rem;'>{sensor_count} sensors</span>"
        f"&nbsp;&nbsp;<span style='color:{color}; font-size:0.8rem; font-weight:600;'>{severity}</span>"
        f"</div>"
    )

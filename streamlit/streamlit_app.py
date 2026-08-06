import streamlit as st

from components.styles import inject_css
from utils.data import get_facilities, get_sensors, get_audit_cases, get_escalations_30d
from views import overview, dashboard, audit_trail, chatbot

st.set_page_config(
    page_title="GeoSense Monitoring AI",
    page_icon="⛰",
    layout="wide"
)

inject_css()

# --- Load data ---
facilities = get_facilities()
sensors = get_sensors()
audit_cases = get_audit_cases()
escalations = get_escalations_30d()

# --- Sidebar ---
st.sidebar.markdown(
    "<div style='padding:8px 0 16px 0;'>"
    "<h3 style='margin:0; color:#f1f5f9;'>GeoSense Monitoring AI</h3>"
    "<p style='margin:4px 0 0 0; color:#6ee7b7; font-size:0.75rem;'>v1.0 — Freeport Tembagapura</p>"
    "</div>",
    unsafe_allow_html=True
)
st.sidebar.markdown("")

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Dashboard", "Case Audit Trail", "Data Chatbot"],
    format_func=lambda x: {
        "Overview": "\u2139\u2003Overview",
        "Dashboard": "\u2318\u2003Dashboard",
        "Case Audit Trail": "\u2637\u2003Audit Trail",
        "Data Chatbot": "\u2734\u2003Chatbot"
    }[x],
    label_visibility="collapsed"
)

st.sidebar.markdown("")
st.sidebar.markdown("")
st.sidebar.markdown(
    f"<span style='color:#6ee7b7; font-size:0.75rem;'>{len(facilities)} facilities &bull; {len(sensors)} sensors</span>",
    unsafe_allow_html=True
)

# --- Page Router ---
if page == "Overview":
    overview.render()
elif page == "Dashboard":
    dashboard.render(facilities, sensors, audit_cases, escalations)
elif page == "Case Audit Trail":
    audit_trail.render(facilities, audit_cases)
elif page == "Data Chatbot":
    chatbot.render()

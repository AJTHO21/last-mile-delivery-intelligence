"""P002 local dashboard entry point."""
import streamlit as st

from dashboard_controls import select_timing_cohort

page = st.navigation([
    st.Page("executive_overview.py", title="Executive Overview", default=True),
    st.Page("route_performance.py", title="Route Performance & Exceptions"),
    st.Page("distance_quality.py", title="Distance Deviations & Data Quality"),
])
with st.sidebar:
    st.session_state.p002_navigation_cohort = select_timing_cohort()
st.html("""
<style>
@media (max-width: 720px) {
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]) {flex-wrap: wrap;}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important; min-width: 0; width: 100% !important;
    }
}
</style>
""")
page.run()

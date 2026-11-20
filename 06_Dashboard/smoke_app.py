"""Minimal local Streamlit smoke screen for the P002 reporting contract."""
import psycopg
import streamlit as st

from dashboard_smoke_data import read_overview


st.set_page_config(page_title="P002 reporting smoke test", layout="wide")
st.title("P002 reporting smoke test")
st.caption("Full workbook · PostgreSQL reporting view")

try:
    overview = read_overview()
except psycopg.Error:
    st.error("PostgreSQL connection or overview query failed. Check the local reporting login and follow the smoke-test runbook.")
except ValueError:
    st.error("PostgreSQL responded, but the overview row failed validation.")
else:
    st.success("PostgreSQL connected as p002_report")
    routes, eligible, late, rate = st.columns(4)
    routes.metric("Routes", f"{overview.route_count:,}")
    eligible.metric("Eligible deliveries", f"{overview.eligible_delivery_count:,}")
    late.metric("Late deliveries", f"{overview.late_count:,}")
    rate.metric("Late-delivery rate", f"{overview.late_delivery_rate:.2%}")

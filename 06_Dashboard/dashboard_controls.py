"""Shared dashboard timing selection."""
import streamlit as st

from executive_overview_data import TIMING_COHORTS


def select_timing_cohort():
    return st.selectbox(
        "Timing cohort", options=tuple(TIMING_COHORTS),
        format_func=TIMING_COHORTS.__getitem__, key="p002_timing_cohort",
    )


def active_timing_cohort():
    if "p002_navigation_cohort" in st.session_state:
        return st.session_state.p002_navigation_cohort
    return select_timing_cohort()

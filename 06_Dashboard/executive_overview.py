"""Page 1 of the P002 dispatch dashboard."""
import altair as alt
import pandas as pd
import psycopg
import streamlit as st

from dashboard_controls import active_timing_cohort
from executive_overview_data import TIMING_COHORTS, read_executive_data

SLATE = "#182431"
BLUE = "#58758C"
ORANGE = "#B34F2B"
PALE = "#EDF2F6"
WORKBOOK = "Workbook v1"


def percent(value):
    return f"{value:.2%}" if value is not None else "Unavailable"


def minutes(value):
    return f"{value:,.2f} min" if value is not None else "Unavailable"


def fraction(numerator, denominator):
    return f"{numerator:,} / {denominator:,}"


@st.cache_data(ttl=120, max_entries=4, show_spinner=False)
def load_data(workbook, cohort):
    return read_executive_data(cohort)


def render_arrivals(overview):
    st.subheader("Arrival-window outcomes")
    denominator = overview["eligible_delivery_count"]
    if not denominator:
        st.info("No eligible delivery visits in this cohort.")
        return
    labels = ("Early", "In window", "Late")
    rows = [
        {"Outcome": label, "Visits": overview[key], "Share": overview[key] / denominator, "Order": index}
        for index, (label, key) in enumerate(zip(labels, ("early_count", "in_window_count", "late_count")))
    ]
    chart = alt.Chart(pd.DataFrame(rows)).mark_bar(size=34).encode(
        x=alt.X("Share:Q", stack="zero", title="Share of eligible deliveries (%)",
                scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        color=alt.Color("Outcome:N", sort=list(labels),
                        scale=alt.Scale(domain=list(labels), range=["#8B9BA8", BLUE, ORANGE])),
        order=alt.Order("Order:Q", sort="ascending"),
        tooltip=["Outcome:N", alt.Tooltip("Visits:Q", format=","), alt.Tooltip("Share:Q", format=".2%")],
    ).properties(height=110, description="Early, in-window and late shares of eligible deliveries.")
    st.altair_chart(chart, width="stretch")
    st.caption(" · ".join(f'{row["Outcome"]}: {row["Visits"]:,} ({row["Share"]:.2%})' for row in rows))
    st.caption(f"Denominator: {denominator:,} eligible delivery visits. Early arrival can reflect waiting before service.")


def render_comparison(crude, standardized):
    st.subheader("Late routes by address order")
    groups = (("Changed", "changed"), ("Unchanged", "unchanged"))
    methods = (("Crude", crude), ("Standardized", standardized))
    points = [
        {"Method": method, "Address order": label, "Rate": float(record[f"{key}_route_rate"])}
        for method, record in methods if record is not None
        for label, key in groups if record[f"{key}_route_rate"] is not None
    ]
    if points:
        chart = alt.Chart(pd.DataFrame(points)).encode(
            x=alt.X("Rate:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"),
                    title="Eligible routes with a late arrival (%)"),
            y=alt.Y("Method:N", sort=["Crude", "Standardized"], title=None),
        )
        line = chart.mark_line(color="#9BAAB7", strokeWidth=2).encode(detail="Method:N")
        dots = chart.mark_point(filled=True, size=100).encode(
            color=alt.Color("Address order:N", scale=alt.Scale(domain=["Changed", "Unchanged"], range=[BLUE, SLATE])),
            shape=alt.Shape("Address order:N", scale=alt.Scale(domain=["Changed", "Unchanged"],
                                                             range=["circle", "diamond"])),
            tooltip=["Method:N", "Address order:N", alt.Tooltip("Rate:Q", format=".2%")],
        )
        st.altair_chart((line + dots).properties(height=145, description="Crude and standardized late-route rates by address order."), width="stretch")

    if crude:
        st.caption("Crude · " + " · ".join(
            f'{label}: {percent(crude[f"{key}_route_rate"])} '
            f'({fraction(crude[f"{key}_late_route_count"], crude[f"{key}_eligible_route_count"])})'
            for label, key in groups
        ))
    else:
        st.caption("Crude comparison unavailable.")
    if standardized and standardized["supported_strata"]:
        st.caption("Standardized · " + " · ".join(
            f'{label}: {percent(standardized[f"{key}_route_rate"])}' for label, key in groups
        ))
        st.caption(
            f'{standardized["supported_strata"]} of {standardized["observed_strata"]} strata supported · '
            f'{fraction(standardized["supported_pooled_eligible_routes"], standardized["observed_pooled_eligible_routes"])} '
            "pooled eligible routes covered."
        )
    else:
        st.caption("Standardized comparison unavailable. No supported strata.")

    with st.expander("Delivery-level comparison"):
        if crude:
            for label, key in groups:
                st.write(
                    f'{label} · crude {percent(crude[f"{key}_delivery_rate"])} '
                    f'({fraction(crude[f"{key}_late_delivery_count"], crude[f"{key}_eligible_delivery_count"])} eligible deliveries) '
                    f'· standardized {percent(standardized[f"{key}_delivery_rate"] if standardized else None)}'
                )
        st.caption("Standardized delivery rates use visit rates within each stratum and common eligible-route weights.")


def main():
    st.set_page_config(page_title="P002 · Executive Overview", layout="wide")
    st.html(f"""
        <style>
        .stApp {{color:{SLATE};}}
        [data-testid="stMetric"] {{background:{PALE}; border:1px solid #D6DFE7;
            padding:0.85rem 1rem; border-radius:0.65rem; color:{SLATE};}}
        [data-testid="stMetric"] label, [data-testid="stMetricValue"] {{color:{SLATE};}}
        </style>
    """)
    st.title("Executive Overview")
    st.caption(f"Last-mile dispatch intelligence · {WORKBOOK}")
    cohort = active_timing_cohort()
    try:
        data = load_data(WORKBOOK, cohort)
    except (psycopg.Error, ValueError):
        st.error("PostgreSQL reporting data is unavailable. Check the local reporting login and deployment, then refresh.")
        return

    overview = data.overview
    st.header(TIMING_COHORTS[cohort])
    late, routes, severity, sequence = st.columns(4)
    late.metric("Late-delivery rate", percent(overview["late_delivery_rate"]))
    late.caption(f'{fraction(overview["late_count"], overview["eligible_delivery_count"])} eligible deliveries')
    routes.metric("Routes with late arrivals", percent(overview["late_route_rate"]))
    routes.caption(f'{fraction(overview["late_route_count"], overview["eligible_route_count"])} eligible routes')
    severity.metric("Median lateness", minutes(overview["median_late_minutes"]))
    severity.caption(f'P90 {minutes(overview["p90_late_minutes"])} · {overview["late_count"]:,} late deliveries')
    sequence.metric("Changed address order", percent(overview["changed_address_route_rate"]))
    sequence.caption(f'{fraction(overview["changed_address_route_count"], overview["valid_sequence_route_count"])} valid routes')

    st.divider()
    left, right = st.columns((1, 1.35))
    with left:
        render_arrivals(overview)
    with right:
        render_comparison(data.crude, data.standardized)

    st.subheader("Timing sensitivity")
    if data.removed:
        removed = data.removed
        status = "Included in this view" if cohort == "full" else "Excluded from this view"
        st.caption(
            f'Routes with spans over 1,440 minutes · {status}: {removed["route_count"]:,} routes, '
            f'{removed["eligible_delivery_count"]:,} eligible deliveries and {removed["late_count"]:,} late deliveries.'
        )
    else:
        st.caption("No separate counts are available for routes above the timing threshold.")
    st.caption("Timing spans use recorded arrival and window offsets. The screen can also omit valid long routes.")

    with st.expander("Definitions and limitations", expanded=True):
        st.write(
            "Delivery rates use eligible non-depot deliveries with valid timing. Route rates use routes with at least "
            "one eligible delivery. Standardization uses common country and route-size weights and includes only strata "
            "with at least 50 eligible routes and 100 eligible deliveries in each address group."
        )
        st.write(
            "Comparisons are observational. Route mix and unmeasured operating conditions can influence results. "
            "Times are relative minutes. Distance elsewhere in this project uses straight-line geodesic kilometers."
        )


main()

"""Page 3 of the local dispatch dashboard."""
import altair as alt
import pandas as pd
import psycopg
import streamlit as st

from dashboard_controls import active_timing_cohort
from distance_quality_data import CATEGORIES, REVIEWS, read_quality_page, read_summary
from executive_overview_data import TIMING_COHORTS
from route_performance_data import ADDRESS_STATES, COUNTRIES, ROUTE_LIMIT, SIZES, Scope, route_id_from_search

BLUE, SLATE, ORANGE = "#58758C", "#182431", "#B34F2B"
ERROR = "PostgreSQL reporting data is unavailable. Check the local reporting login and deployment."


def fmt(value, pattern=",.2f"):
    return format(value, pattern) if value is not None else "Unavailable"


@st.cache_data(ttl=120, max_entries=80, show_spinner=False)
def load_summary(scope, address):
    return read_summary(scope, address)


@st.cache_data(ttl=120, max_entries=60, show_spinner=False)
def load_quality(scope, address, category, review, search, page):
    return read_quality_page(scope, address, category, review, search, page)


def render_summary(scope, address):
    try:
        rollup, categories = load_summary(scope, address)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return
    if rollup is None:
        st.info("No routes match the selected scope.")
        return
    labels = [category.title() for category in CATEGORIES if category != "missing" or category in categories]
    counts = [{"Category": label, "Routes": categories.get(label.lower(), {}).get("route_count", 0)}
              for label in labels]
    with st.container():
        st.subheader("Routes by recorded distance change")
        st.altair_chart(alt.Chart(pd.DataFrame(counts)).mark_bar(color=BLUE).encode(
            x=alt.X("Category:N", sort=labels, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("Routes:Q"),
            tooltip=["Category:N", alt.Tooltip("Routes:Q", format=",")],
        ).properties(height=160), width="stretch")
        st.caption(" · ".join(f'{row["Category"]}: {row["Routes"]:,}' for row in counts))
    with st.container():
        st.subheader("Late arrivals by distance category")
        left, right = st.columns(2)
        for panel, endpoint, title in ((left, "route", "Late routes"), (right, "delivery", "Late deliveries")):
            entries = []
            for label in labels:
                row = categories.get(label.lower(), {})
                entries.append({"Category": label, "Late": row.get(f"late_{endpoint}_count", 0),
                                "Eligible": row.get(f"eligible_{endpoint}_count", 0),
                                "Rate": row.get(f"late_{endpoint}_rate")})
            with panel:
                st.markdown(f"**{title}**")
                points = [dict(row, Rate=float(row["Rate"])) for row in entries if row["Rate"] is not None]
                if points:
                    st.altair_chart(alt.Chart(pd.DataFrame(points)).mark_bar(color=ORANGE).encode(
                        y=alt.Y("Category:N", sort=labels, title=None),
                        x=alt.X("Rate:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"), title=None),
                        tooltip=["Category:N", "Late:Q", "Eligible:Q", alt.Tooltip("Rate:Q", format=".2%")],
                    ).properties(height=110), width="stretch")
                for row in entries:
                    st.caption(f'{row["Category"]}: {row["Late"]:,} / {row["Eligible"]:,} eligible · {fmt(row["Rate"], ".2%")}')

    st.subheader("Paired distance change")
    quantiles = {label: rollup[key] for label, key in (
        ("P05", "p05_signed_difference_km"), ("Median", "median_signed_difference_km"),
        ("P95", "p95_signed_difference_km"),
    )}
    st.caption(f'Actual minus planned · geodesic km · {rollup["route_count"]:,} scoped routes · '
               f'{rollup["distance_review_route_count"]:,} distance-review routes')
    for container, (label, value) in zip(st.columns(3), quantiles.items()):
        container.metric(f"{label} (geodesic km)", fmt(value))
    if all(value is not None for value in quantiles.values()):
        dots = alt.Chart(pd.DataFrame([{"Quantile": label, "Geodesic km": float(value)}
                                      for label, value in quantiles.items()])).mark_point(
            color=BLUE, filled=True, size=100).encode(
                x=alt.X("Geodesic km:Q", title="Actual minus planned (geodesic km)", scale=alt.Scale(zero=True)),
                y=alt.Y("Quantile:N", sort=list(quantiles), title=None),
                tooltip=["Quantile:N", alt.Tooltip("Geodesic km:Q", format=",.2f")])
        zero = alt.Chart(pd.DataFrame({"Reference": [0]})).mark_rule(color=SLATE, strokeDash=[4, 4]).encode(x="Reference:Q")
        st.altair_chart((zero + dots).properties(height=105, description="P05, median and P95 signed distance change, compared with zero."), width="stretch")


def flags(row):
    labels = [label for key, label in (
        ("route_timing_span_over_1440", "Span >1,440 min"), ("has_arrival_reversal", "Arrival reversal"),
        ("zero_planned_distance", "Zero planned"), ("large_distance_gap", "Gap ≥100 km"),
        ("planned_same_address_nonzero_legs", "Nonzero planned same-address leg"),
        ("actual_same_address_nonzero_legs", "Nonzero actual same-address leg"),
    ) if row[key]]
    if row["distance_category"] == "missing":
        labels.append("Missing distance")
    return ", ".join(labels) or "—"


def render_review(scope, address):
    st.subheader("Timing and distance review")
    st.caption("Category, review flags and route-ID search apply only to this table and route inspection.")
    left, middle, right = st.columns(3)
    search = left.text_input("Search by route ID", max_chars=10, placeholder="e.g. 7545")
    category = middle.selectbox("Distance category", (None, *CATEGORIES), format_func=lambda item: item.title() if item else "All categories")
    review = right.selectbox("Review flags", tuple(REVIEWS), format_func=REVIEWS.__getitem__)
    try:
        route_id_from_search(search)
    except ValueError as exc:
        st.warning(str(exc))
        return
    state = st.session_state
    filters = (scope, address, category, review, search.strip())
    if state.get("distance_filters") != filters:
        state.distance_filters = filters
        state.distance_page = 0
        state.distance_inspection_version = state.get("distance_inspection_version", 0) + 1
    page = state.distance_page
    try:
        result = load_quality(scope, address, category, review, search, page)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return
    previous, following, status = st.columns((1, 1, 4))
    previous.button("Previous", disabled=page == 0, on_click=lambda: state.update(distance_page=page - 1))
    following.button("Next", disabled=not result.has_next, on_click=lambda: state.update(distance_page=page + 1))
    if not result.rows:
        st.info("No routes match these review filters.")
        return
    status.caption(f"Page {page + 1:,} · routes {page * ROUTE_LIMIT + 1:,}–{page * ROUTE_LIMIT + len(result.rows):,}")
    st.dataframe([{
        "Route ID": row["route_id"], "Cohort": f'{row["country_name"]} · {row["route_size_band"]}',
        "Category": row["distance_category"].title(), "Signed change (geodesic km)": fmt(row["signed_difference_km"]),
        "Review flags": flags(row),
    } for row in result.rows], hide_index=True, width="stretch")
    records = {(row["route_id"], row["import_id"]): row for row in result.rows}
    selected = st.selectbox("Inspect a route", tuple(records), index=None,
                            format_func=lambda key: f"Route {key[0]:,}",
                            key=f"distance_route_{state.distance_inspection_version}_{page}")
    if selected is not None:
        row = records[selected]
        st.subheader(f'Route {row["route_id"]:,} · recorded distance')
        st.caption(f'{row["country_name"]} · {row["visit_count"]:,} visits · {row["address_sequence_status"]} address order'
                   f' · {row["distance_category"]} · geodesic km')
        with st.expander("Route distance and flag detail", expanded=True):
            for label, key in (
                ("Planned", "planned_geodesic_km"), ("Actual", "actual_geodesic_km"),
                ("Signed change", "signed_difference_km"), ("Absolute change", "absolute_difference_km"),
            ):
                value = row[key]
                st.write(f'{label}: {fmt(value) + " geodesic km" if value is not None else "Unavailable"}')
            value = row["distance_difference_pct"]
            st.metric("Change from planned (%)", f"{fmt(value)}%" if value is not None else "Unavailable")
            st.write(f"Review flags: {flags(row)}")


def main():
    st.set_page_config(page_title="P002 · Distance Deviations & Data Quality", layout="wide")
    st.title("Distance Deviations & Data Quality")
    st.caption("Last-mile dispatch intelligence · Workbook v1 · Straight-line Haversine leg sums")
    timing = active_timing_cohort()
    left, middle, right = st.columns(3)
    country = left.selectbox("Country", (None, *COUNTRIES), format_func=lambda key: COUNTRIES.get(key, "All countries"))
    size = middle.selectbox("Route size", (None, *SIZES), format_func=lambda value: value or "All sizes")
    address = right.selectbox("Address order", (None, *ADDRESS_STATES),
                              format_func=lambda value: value.title() if value else "All address orders")
    scope = Scope(timing, country, size)
    st.caption(f'Selected scope: {TIMING_COHORTS[timing]} · {COUNTRIES.get(country, "All countries")} · '
               f'{size or "All sizes"} · {address or "All address orders"}')
    render_summary(scope, address)
    st.divider()
    render_review(scope, address)
    with st.expander("Definitions and limitations"):
        st.write("Shorter and longer use signed changes outside ±0.000000001 km. Equal includes changes within that band. "
                 "A zero planned total has an unavailable percentage change.")
        st.write("Late-route rates use routes with eligible deliveries. Late-delivery rates use eligible visits. "
                 "The timing sensitivity removes spans above 1,440 minutes. Review flags do not change eligibility.")
        st.write("These observational comparisons use straight-line geodesic distances. Road mileage, driving costs, "
                 "and causal effects require separate evidence.")


main()

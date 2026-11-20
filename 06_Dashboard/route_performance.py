"""Page 2 of the P002 dispatch dashboard."""
import altair as alt
import pandas as pd
import psycopg
import streamlit as st

from dashboard_controls import active_timing_cohort
from executive_overview_data import TIMING_COHORTS
from route_performance_data import (
    ADDRESS_STATES, BANDS, COUNTRIES, FLAGS, ROUTE_LIMIT, SIZES, VISIT_LIMIT, VISIT_STATES,
    Scope, read_comparison, read_displacement, read_route_page, read_visits, route_id_from_search,
)

SLATE = "#182431"
BLUE = "#58758C"
ORANGE = "#B34F2B"
ADDRESS_LABELS = {"changed": "Changed", "unchanged": "Unchanged", "unverified": "Unverified"}
VISIT_LABELS = {"changed_visit_order": "Changed", "exact_visit_order": "Exact", "unverified": "Unverified"}
FLAG_LABELS = {"late": "Late arrival", "timing": "Timing review", "distance": "Distance review"}
ERROR = "PostgreSQL reporting data is unavailable. Check the local reporting login and deployment."


def rate(value):
    return f"{value:.2%}" if value is not None else "Unavailable"


@st.cache_data(ttl=120, max_entries=80, show_spinner=False)
def load_comparison(scope):
    return read_comparison(scope)


@st.cache_data(ttl=120, max_entries=30, show_spinner=False)
def load_displacement(cohort, address, visit_order):
    return read_displacement(cohort, address, visit_order)


@st.cache_data(ttl=120, max_entries=60, show_spinner=False)
def load_route_page(scope, address, flag, search, page):
    return read_route_page(scope, address, flag, search, page)


@st.cache_data(ttl=120, max_entries=30, show_spinner=False)
def load_visits(route_id, import_id, page):
    return read_visits(route_id, import_id, page)


def render_comparison(scope):
    st.subheader("Late routes by address order")
    st.caption("Country × route size · late routes / routes with eligible deliveries")
    try:
        rows = load_comparison(scope)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return
    if not rows:
        st.info("No matching route cohorts.")
        return
    points, counts = [], []
    for row in rows:
        label = f'{row["country_name"]} · {row["route_size_band"]}'
        detail = {"Cohort": label}
        for status in ("changed", "unchanged"):
            group = ADDRESS_LABELS[status]
            late = row[f"{status}_late_route_count"]
            eligible = row[f"{status}_eligible_route_count"]
            total = row[f"{status}_route_count"]
            proportion = row[f"{status}_route_rate"]
            detail[group] = f"{late:,} / {eligible:,} ({rate(proportion)}) · {total:,} routes"
            if proportion is not None:
                points.append({"Cohort": label, "Address order": group, "Rate": float(proportion),
                               "Late routes": late, "Eligible routes": eligible, "Total routes": total})
        counts.append(detail)
    if points:
        chart = alt.Chart(pd.DataFrame(points)).mark_point(filled=True, size=75).encode(
            x=alt.X("Rate:Q", title="Late-route rate (%)", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            y=alt.Y("Cohort:N", sort=[row["Cohort"] for row in counts], title=None),
            color=alt.Color("Address order:N", scale=alt.Scale(domain=["Changed", "Unchanged"], range=[BLUE, SLATE])),
            shape=alt.Shape("Address order:N", scale=alt.Scale(domain=["Changed", "Unchanged"], range=["circle", "diamond"])),
            tooltip=["Cohort:N", "Address order:N", alt.Tooltip("Rate:Q", format=".2%"),
                     "Late routes:Q", "Eligible routes:Q", "Total routes:Q"],
        ).properties(height=max(120, 30 * len(counts)))
        st.altair_chart(chart, width="stretch")
    st.dataframe(counts, hide_index=True, width="stretch")


def render_displacement(cohort):
    st.subheader("Displacement and late deliveries")
    st.caption("All countries and route sizes · timing and order filters below")
    one, two = st.columns(2)
    address = one.selectbox("Displacement address order", ADDRESS_STATES, format_func=ADDRESS_LABELS.__getitem__)
    visit_order = two.selectbox("Displacement visit order", VISIT_STATES, format_func=VISIT_LABELS.__getitem__)
    try:
        rows = load_displacement(cohort, address, visit_order)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return
    if not rows:
        st.info("No visits in this combination of address and visit order.")
        return
    counts = [{"Positions": row["displacement_band"], "Visits": row["visit_count"],
               "Represented routes": row["represented_route_count"],
               "Eligible deliveries": row["eligible_delivery_count"], "Late deliveries": row["late_delivery_count"],
               "Late-delivery rate": rate(row["late_delivery_rate"])} for row in rows]
    points = [dict(record, Rate=float(row["late_delivery_rate"])) for record, row in zip(counts, rows)
              if row["late_delivery_rate"] is not None]
    if points:
        chart = alt.Chart(pd.DataFrame(points)).mark_point(color=ORANGE, filled=True, size=75).encode(
            x=alt.X("Rate:Q", title="Late-delivery rate (%)", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            y=alt.Y("Positions:N", sort=list(BANDS), title="Position shift"),
            tooltip=["Positions:N", alt.Tooltip("Rate:Q", format=".2%"), "Visits:Q",
                     "Represented routes:Q", "Eligible deliveries:Q", "Late deliveries:Q"],
        ).properties(height=max(120, 30 * len(counts)))
        st.altair_chart(chart, width="stretch")
    st.dataframe(counts, hide_index=True, width="stretch")
    st.caption("Routes can appear in more than one band. Zero shift is measured per visit.")


def route_flags(row):
    return ", ".join(label for key, label in (
        ("has_late_arrival", "Late"), ("route_timing_span_over_1440", "Span >1,440 min"),
        ("has_arrival_reversal", "Arrival reversal"), ("distance_review_flag", "Distance review"),
    ) if row[key]) or "—"


def show_visit_drill(row, context_key):
    st.subheader(f'Route {row["route_id"]:,} · visit detail')
    st.caption(
        f'{row["country_name"]} · {row["visit_count"]:,} visits · '
        f'{row["late_delivery_visit_count"]:,} late / {row["eligible_delivery_visit_count"]:,} eligible deliveries. '
        "Sorted by recorded actual visit position. All timing values are route-relative minutes."
    )
    last_page = max(0, (row["visit_count"] - 1) // VISIT_LIMIT)
    page = 0
    if last_page:
        page = int(st.number_input("Visit page", min_value=1, max_value=last_page + 1, step=1,
                                   key=f'{context_key}_visit_page_{row["route_id"]}_{row["import_id"]}')) - 1
    try:
        visits = load_visits(row["route_id"], row["import_id"], page)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return
    if not visits:
        st.info("No visits were returned for this route page.")
        return

    def flags(visit):
        return ", ".join(label for key, label in (
            ("arrival_tie", "Tie"), ("arrival_reversal", "Reversal"), ("zero_width_window", "Zero-width window"),
            ("depot_delivery_overlap", "Depot/delivery overlap"), ("route_timing_span_over_1440", "Span >1,440 min"),
            ("early_gap_over_1440", "Early gap >1,440 min"), ("late_gap_over_1440", "Late gap >1,440 min"),
        ) if visit[key]) or "—"

    st.caption(f"Showing visits {page * VISIT_LIMIT + 1:,}–{page * VISIT_LIMIT + len(visits):,}.")
    st.dataframe(pd.DataFrame([{
        "Actual": visit["index_a"], "Planned": visit["index_p"], "Stop ID": visit["stop_id"],
        "Address ID": visit["address_id"],
        "Outcome": (visit["arrival_status"] or "Not classified").replace("_", " "),
        "Late (min)": visit["late_minutes"], "Flags": flags(visit),
    } for visit in visits]), hide_index=True, width="stretch")
    with st.expander("Visit timing, eligibility and source detail"):
        st.caption("Actual position links these rows to the summary. Times are route-relative minutes.")
        st.dataframe(pd.DataFrame([{
            "Actual": visit["index_a"], "Earliest (min)": visit["earliest_minutes"],
            "Arrival (min)": visit["arrived_minutes"], "Latest (min)": visit["latest_minutes"],
            "Early (min)": visit["early_minutes"], "Timing span (min)": visit["route_timing_span_minutes"],
        } for visit in visits]), hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame([{
            "Actual": visit["index_a"], "Depot": visit["depot"], "Delivery": visit["delivery"],
            "Eligible": visit["eligible_delivery"], "Eligibility reason": visit["eligibility_reason"].replace("_", " "),
            "Source row": f'{visit["worksheet_name"]}:{visit["source_row_number"]}',
        } for visit in visits]), hide_index=True, width="stretch")


def render_routes(scope):
    st.subheader("Route exceptions")
    st.caption("Uses the timing, country, and size filters above. Search and exception filters apply to this list only.")
    left, middle, right = st.columns(3)
    search = left.text_input("Search by route ID", placeholder="e.g. 7545", max_chars=10)
    address = middle.selectbox("Table address order", (None, *ADDRESS_STATES),
                               format_func=lambda value: ADDRESS_LABELS.get(value, "All"))
    flag = right.selectbox("Exception filter", (None, *FLAGS), format_func=lambda value: FLAG_LABELS.get(value, "All routes"))
    try:
        route_id_from_search(search)
    except ValueError as exc:
        st.warning(str(exc))
        return

    scope_key = (scope, address, flag, search.strip())
    state = st.session_state
    if state.get("route_scope") != scope_key:
        state.route_scope = scope_key
        state.route_page = 0
        state.route_scope_version = state.get("route_scope_version", 0) + 1
    page = state.route_page
    try:
        result = load_route_page(scope, address, flag, search, page)
    except (psycopg.Error, ValueError):
        st.error(ERROR)
        return

    previous, following, message = st.columns((1, 1, 4))
    previous.button("Previous", disabled=page == 0, on_click=lambda: state.update(route_page=page - 1))
    following.button("Next", disabled=not result.has_next, on_click=lambda: state.update(route_page=page + 1))
    if not result.rows:
        message.caption(f"Page {page + 1:,}")
        st.info("No routes match this scope and search.")
        return

    message.caption(f"Page {page + 1:,} · routes {page * ROUTE_LIMIT + 1:,}–{page * ROUTE_LIMIT + len(result.rows):,} in this result")
    st.dataframe(pd.DataFrame([{
        "Route ID": row["route_id"], "Cohort": f'{row["country_name"]} · {row["route_size_band"]}',
        "Address order": ADDRESS_LABELS[row["address_sequence_status"]],
        "Late / eligible": f'{row["late_delivery_visit_count"]:,} / {row["eligible_delivery_visit_count"]:,}',
        "Late delivery (%)": rate(row["late_delivery_rate"]), "Exceptions": route_flags(row),
    } for row in result.rows]), hide_index=True, width="stretch")

    by_key = {(row["route_id"], row["import_id"]): row for row in result.rows}
    context_key = f'route_drill_{state.route_scope_version}_{page}'
    selection = st.selectbox("Select a route to inspect", tuple(by_key), index=None,
                             format_func=lambda key: f'Route {key[0]:,} · {by_key[key]["country_name"]}',
                             key=context_key)
    if selection is not None:
        row = by_key[selection]
        with st.expander("Selected route sequence detail"):
            visit_order = {True: "Exact", False: "Changed", None: "Unverified"}[row["exact_visit_match"]]
            st.write(f'{visit_order} visit order · {row["moved_visit_count"]:,} moved / {row["visit_count"]:,} visits')
        show_visit_drill(row, context_key)


def main():
    st.set_page_config(page_title="P002 · Route Performance & Exceptions", layout="wide")
    st.title("Route Performance & Exceptions")
    st.caption("Last-mile dispatch intelligence · Workbook v1 · Observational comparisons")
    cohort = active_timing_cohort()
    country, size = st.columns(2)
    country_code = country.selectbox("Country", (None, *COUNTRIES), format_func=lambda value: COUNTRIES.get(value, "All countries"))
    size_band = size.selectbox("Route size", (None, *SIZES), format_func=lambda value: value or "All sizes")
    scope = Scope(cohort, country_code, size_band)
    st.caption(f'Selected scope: {TIMING_COHORTS[cohort]} · {COUNTRIES.get(country_code, "All countries")} · {size_band or "All sizes"}')
    left, right = st.columns(2)
    with left:
        render_comparison(scope)
    with right:
        render_displacement(cohort)
    st.divider()
    render_routes(scope)
    with st.expander("Definitions and limitations"):
        st.write(
            "A late route has at least one eligible late delivery. A late-delivery rate counts late visits among "
            "eligible deliveries. Size includes all visits. A timing review here means an arrival reversal or a "
            "span above 1,440 minutes. Early arrival can reflect waiting before service."
        )
        st.write(
            "Comparisons are descriptive. Route mix and unmeasured operating conditions can influence results. "
            "Distances flagged elsewhere in the dashboard are straight-line geodesic measures."
        )


main()

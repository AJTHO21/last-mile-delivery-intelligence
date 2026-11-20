"""Bounded Page 2 reads from the approved reporting schema."""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from executive_overview_data import TIMING_COHORTS

COUNTRIES = {0: "Norway", 1: "Denmark"}
SIZES = ("1–5", "6–10", "11–20", "21+")
ADDRESS_STATES = ("changed", "unchanged", "unverified")
VISIT_STATES = ("changed_visit_order", "exact_visit_order", "unverified")
BANDS = ("0", "1", "2–3", "4–6", "7+")
ROUTE_LIMIT = 25
VISIT_LIMIT = 50
FLAGS = ("late", "timing", "distance")

COMPARISON_SQL = """
    SELECT country, country_name, route_size_band,
           changed_route_count, unchanged_route_count,
           changed_eligible_route_count, unchanged_eligible_route_count,
           changed_late_route_count, unchanged_late_route_count,
           changed_route_rate, unchanged_route_rate
    FROM reporting.route_performance_comparison
    WHERE timing_cohort = %(cohort)s AND country IS NOT NULL AND route_size_band IS NOT NULL
      AND (%(country)s::smallint IS NULL OR country = %(country)s)
      AND (%(size)s::text IS NULL OR route_size_band = %(size)s)
    ORDER BY country, array_position(ARRAY['1–5','6–10','11–20','21+'], route_size_band)
"""

DISPLACEMENT_SQL = """
    SELECT displacement_band, visit_count, represented_route_count, eligible_delivery_count,
           late_delivery_count, late_delivery_rate
    FROM reporting.visit_displacement_lateness
    WHERE timing_cohort = %s AND address_status = %s AND visit_order_status = %s
    ORDER BY array_position(ARRAY['0','1','2–3','4–6','7+'], displacement_band)
"""

ROUTES_SQL = """
    SELECT route_id, import_id, country_name, route_size_band, visit_count, address_sequence_status,
           exact_visit_match, moved_visit_count, eligible_delivery_visit_count, late_delivery_visit_count,
           late_delivery_rate, has_late_arrival, route_timing_span_over_1440, has_arrival_reversal,
           distance_review_flag
    FROM reporting.dashboard_route
    WHERE (%(country)s::smallint IS NULL OR country = %(country)s)
      AND (%(size)s::text IS NULL OR route_size_band = %(size)s)
      AND (%(cohort)s = 'full' OR NOT route_timing_span_over_1440)
      AND (%(address)s::text IS NULL OR address_sequence_status = %(address)s)
      AND (%(route_id)s::integer IS NULL OR route_id = %(route_id)s)
      AND CASE %(flag)s::text
          WHEN 'late' THEN has_late_arrival
          WHEN 'timing' THEN route_timing_span_over_1440 OR has_arrival_reversal
          WHEN 'distance' THEN distance_review_flag
          ELSE true END
    ORDER BY late_delivery_visit_count DESC, route_id, import_id
    LIMIT %(limit)s OFFSET %(offset)s
"""

VISITS_SQL = """
    SELECT worksheet_name, source_row_number, index_p, index_a, stop_id, address_id, depot, delivery,
           arrived_minutes, earliest_minutes, latest_minutes, eligible_delivery, eligibility_reason,
           arrival_status, early_minutes, late_minutes, arrival_tie, arrival_reversal, zero_width_window,
           depot_delivery_overlap, route_timing_span_minutes, route_timing_span_over_1440,
           early_gap_over_1440, late_gap_over_1440
    FROM reporting.dashboard_visit
    WHERE route_id = %s AND import_id = %s
    ORDER BY index_a, index_p, worksheet_name, source_row_number
    LIMIT %s OFFSET %s
"""


@dataclass(frozen=True)
class Scope:
    cohort: str
    country: int | None = None
    size: str | None = None

    def bindings(self):
        if (self.cohort not in TIMING_COHORTS
                or self.country is not None and self.country not in COUNTRIES
                or self.size is not None and self.size not in SIZES):
            raise ValueError("Invalid route scope")
        return {"cohort": self.cohort, "country": self.country, "size": self.size}


@dataclass(frozen=True)
class RoutePage:
    rows: list[dict]
    has_next: bool


@contextmanager
def reporting_connection():
    with psycopg.connect(
        host="127.0.0.1", hostaddr="127.0.0.1", port=5432, dbname="p002_last_mile",
        user="p002_report", passfile=str(Path.home() / ".config" / "p002" / "pgpass"),
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
        connect_timeout=5, row_factory=dict_row,
    ) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        if connection.execute("SELECT current_user AS role").fetchone() != {"role": "p002_report"}:
            raise ValueError("Unexpected PostgreSQL role")
        yield connection


def route_id_from_search(value):
    value = value.strip()
    if not value:
        return None
    if not value.isascii() or not value.isdecimal() or len(value) > 10 or int(value) > 2147483647:
        raise ValueError("Enter a nonnegative numeric route ID")
    return int(value)


def read_comparison(scope):
    with reporting_connection() as connection:
        return connection.execute(COMPARISON_SQL, scope.bindings()).fetchall()


def read_displacement(cohort, address, visit_order):
    if cohort not in TIMING_COHORTS or address not in ADDRESS_STATES or visit_order not in VISIT_STATES:
        raise ValueError("Invalid displacement scope")
    with reporting_connection() as connection:
        return connection.execute(DISPLACEMENT_SQL, (cohort, address, visit_order)).fetchall()


def read_route_page(scope, address, flag, search, page):
    route_id = route_id_from_search(search)
    if page < 0 or (address is not None and address not in ADDRESS_STATES) or (flag is not None and flag not in FLAGS):
        raise ValueError("Invalid route-table filters")
    bindings = dict(scope.bindings(), address=address, flag=flag, route_id=route_id,
                    limit=ROUTE_LIMIT + 1, offset=page * ROUTE_LIMIT)
    with reporting_connection() as connection:
        rows = connection.execute(ROUTES_SQL, bindings).fetchall()
    return RoutePage(rows[:ROUTE_LIMIT], len(rows) > ROUTE_LIMIT)


def read_visits(route_id, import_id, page):
    if route_id < 0 or import_id <= 0 or page < 0:
        raise ValueError("Invalid route selection")
    with reporting_connection() as connection:
        return connection.execute(VISITS_SQL, (route_id, import_id, VISIT_LIMIT, page * VISIT_LIMIT)).fetchall()

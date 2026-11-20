"""Read the approved Page 1 reporting datasets in one local snapshot."""
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

TIMING_COHORTS = {
    "full": "Full workbook",
    "span_at_most_1440": "Timing span ≤1,440 minutes",
}

OVERVIEW_SQL = """
    SELECT timing_cohort, eligible_delivery_count, early_count, in_window_count, late_count,
           eligible_route_count, late_route_count, valid_sequence_route_count,
           changed_address_route_count, late_delivery_rate, late_route_rate,
           changed_address_route_rate, median_late_minutes, p90_late_minutes, route_count
    FROM reporting.dashboard_overview
    WHERE timing_cohort IN (%s, 'removed_over_1440')
"""
CRUDE_SQL = """
    SELECT changed_eligible_route_count, unchanged_eligible_route_count,
           changed_late_route_count, unchanged_late_route_count,
           changed_route_rate, unchanged_route_rate,
           changed_eligible_delivery_count, unchanged_eligible_delivery_count,
           changed_late_delivery_count, unchanged_late_delivery_count,
           changed_delivery_rate, unchanged_delivery_rate, route_gap_pp, delivery_gap_pp
    FROM reporting.route_performance_comparison
    WHERE timing_cohort = %s AND country IS NULL AND route_size_band IS NULL
"""
STANDARDIZED_SQL = """
    SELECT supported_strata, observed_strata, supported_pooled_eligible_routes,
           observed_pooled_eligible_routes, changed_route_rate, unchanged_route_rate,
           changed_delivery_rate, unchanged_delivery_rate, route_gap_pp, delivery_gap_pp
    FROM reporting.route_performance_standardized WHERE timing_cohort = %s
"""


@dataclass(frozen=True)
class ExecutiveData:
    overview: dict
    removed: dict | None
    crude: dict | None
    standardized: dict | None


def optional_row(rows):
    if len(rows) > 1:
        raise ValueError("Reporting dataset returned duplicate aggregate rows")
    return rows[0] if rows else None


def read_executive_data(cohort: str) -> ExecutiveData:
    if cohort not in TIMING_COHORTS:
        raise ValueError("Unknown timing cohort")

    # Keep the separately runnable Task 015 smoke app independent.
    with psycopg.connect(
        host="127.0.0.1", hostaddr="127.0.0.1", port=5432,
        dbname="p002_last_mile", user="p002_report",
        passfile=str(Path.home() / ".config" / "p002" / "pgpass"),
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
        connect_timeout=5, row_factory=dict_row,
    ) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        identity = connection.execute("SELECT current_user AS role").fetchone()
        if identity != {"role": "p002_report"}:
            raise ValueError("Unexpected PostgreSQL role")
        overview_rows = connection.execute(OVERVIEW_SQL, (cohort,)).fetchall()
        crude = optional_row(connection.execute(CRUDE_SQL, (cohort,)).fetchall())
        standardized = optional_row(connection.execute(STANDARDIZED_SQL, (cohort,)).fetchall())

    overview = optional_row([row for row in overview_rows if row["timing_cohort"] == cohort])
    removed = optional_row([row for row in overview_rows if row["timing_cohort"] == "removed_over_1440"])
    if overview is None:
        raise ValueError("Selected overview cohort is unavailable")
    if sum(overview[key] for key in ("early_count", "in_window_count", "late_count")) != overview["eligible_delivery_count"]:
        raise ValueError("Arrival outcomes do not reconcile to the eligible delivery denominator")
    return ExecutiveData(overview, removed, crude, standardized)

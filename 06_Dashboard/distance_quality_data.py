"""Bounded Page 3 queries against approved route-grain reporting views."""
from route_performance_data import ADDRESS_STATES, ROUTE_LIMIT, RoutePage, reporting_connection, route_id_from_search

CATEGORIES = ("shorter", "equal", "longer", "missing")
REVIEWS = {
    "any": "Any review flag",
    "timing": "Timing review",
    "distance": "Distance review",
    "all": "All routes",
}

SUMMARY_SQL = """
    SELECT distance_category, route_count, eligible_route_count, late_route_count,
           eligible_delivery_count, late_delivery_count, late_route_rate, late_delivery_rate,
           p05_signed_difference_km, median_signed_difference_km, p95_signed_difference_km,
           distance_review_route_count
    FROM reporting.route_distance_comparison
    WHERE timing_cohort = %(cohort)s
      AND country IS NOT DISTINCT FROM %(country)s::smallint
      AND route_size_band IS NOT DISTINCT FROM %(size)s::text
      AND address_sequence_status IS NOT DISTINCT FROM %(address)s::text
    ORDER BY distance_category NULLS FIRST
    LIMIT 5
"""

QUALITY_SQL = """
    SELECT route_id, import_id, country_name, route_size_band, visit_count,
           address_sequence_status, distance_category, planned_geodesic_km, actual_geodesic_km,
           signed_difference_km, absolute_difference_km, distance_difference_pct,
           route_timing_span_over_1440, has_arrival_reversal, distance_review_flag,
           zero_planned_distance, large_distance_gap, planned_same_address_nonzero_legs,
           actual_same_address_nonzero_legs
    FROM reporting.dashboard_route
    WHERE (%(country)s::smallint IS NULL OR country = %(country)s)
      AND (%(size)s::text IS NULL OR route_size_band = %(size)s)
      AND (%(address)s::text IS NULL OR address_sequence_status = %(address)s)
      AND (%(cohort)s = 'full' OR NOT route_timing_span_over_1440)
      AND (%(category)s::text IS NULL OR distance_category = %(category)s)
      AND (%(route_id)s::integer IS NULL OR route_id = %(route_id)s)
      AND CASE %(review)s::text
          WHEN 'all' THEN true
          WHEN 'distance' THEN distance_review_flag
          WHEN 'timing' THEN route_timing_span_over_1440 OR has_arrival_reversal
          WHEN 'any' THEN distance_review_flag OR route_timing_span_over_1440 OR has_arrival_reversal
          ELSE false END
    ORDER BY distance_review_flag DESC, absolute_difference_km DESC NULLS LAST, route_id, import_id
    LIMIT %(limit)s OFFSET %(offset)s
"""


def scope_bindings(scope, address):
    if address is not None and address not in ADDRESS_STATES:
        raise ValueError("Invalid address-order filter")
    return dict(scope.bindings(), address=address)


def read_summary(scope, address):
    params = scope_bindings(scope, address)
    with reporting_connection() as connection:
        rows = connection.execute(SUMMARY_SQL, params).fetchall()
    rollups = [row for row in rows if row["distance_category"] is None]
    categories = {row["distance_category"]: row for row in rows if row["distance_category"] is not None}
    if len(rollups) > 1 or len(rollups) + len(categories) != len(rows) or categories.keys() - set(CATEGORIES):
        raise ValueError("Unexpected distance grouping grain")
    if rows and (not rollups or sum(row["route_count"] for row in categories.values()) != rollups[0]["route_count"]):
        raise ValueError("Distance categories do not reconcile to the selected scope")
    return (rollups[0] if rollups else None), categories


def read_quality_page(scope, address, category, review, search, page):
    if page < 0 or review not in REVIEWS or (category is not None and category not in CATEGORIES):
        raise ValueError("Invalid review-table filters")
    params = dict(scope_bindings(scope, address), category=category, review=review,
                  route_id=route_id_from_search(search), limit=ROUTE_LIMIT + 1, offset=page * ROUTE_LIMIT)
    with reporting_connection() as connection:
        rows = connection.execute(QUALITY_SQL, params).fetchall()
    return RoutePage(rows[:ROUTE_LIMIT], len(rows) > ROUTE_LIMIT)

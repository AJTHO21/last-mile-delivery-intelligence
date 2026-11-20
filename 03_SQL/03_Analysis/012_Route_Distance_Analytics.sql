\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog;

DO $$
BEGIN
    IF current_database() <> 'p002_last_mile' OR current_user <> 'p002_dev' THEN
        RAISE EXCEPTION 'Run as p002_dev in p002_last_mile';
    END IF;
END
$$;

CREATE OR REPLACE VIEW reporting.route_distance AS
WITH legs AS (
    SELECT visit.*,
           lag(address_id) OVER (PARTITION BY route_id, import_id ORDER BY index_p) AS previous_planned_address,
           lag(address_id) OVER (PARTITION BY route_id, import_id ORDER BY index_a) AS previous_actual_address
    FROM core.visit AS visit
), totals AS (
    SELECT route_id, import_id, count(*) AS distance_visit_count,
           sum(distance_p_km) AS planned_geodesic_km,
           sum(distance_a_km) AS actual_geodesic_km,
           count(*) FILTER (WHERE previous_planned_address = address_id AND distance_p_km <> 0)
               AS planned_same_address_nonzero_legs,
           count(*) FILTER (WHERE previous_actual_address = address_id AND distance_a_km <> 0)
               AS actual_same_address_nonzero_legs
    FROM legs
    GROUP BY route_id, import_id
), differences AS (
    SELECT totals.*, actual_geodesic_km - planned_geodesic_km AS signed_difference_km
    FROM totals
)
SELECT route.route_id, route.import_id, route.country, route.country_name,
       route.route_size_band, route.visit_count,
       coalesce(distance_visit_count, 0) AS distance_visit_count,
       route.exact_address_match,
       CASE route.exact_address_match WHEN true THEN 'unchanged' WHEN false THEN 'changed'
            ELSE 'unverified' END AS address_sequence_status,
       planned_geodesic_km, actual_geodesic_km, signed_difference_km,
       abs(signed_difference_km) AS absolute_difference_km,
       100 * signed_difference_km / nullif(planned_geodesic_km, 0) AS distance_difference_pct,
       CASE WHEN signed_difference_km IS NULL THEN 'missing'
            WHEN signed_difference_km < -0.000000001 THEN 'shorter'
            WHEN signed_difference_km > 0.000000001 THEN 'longer'
            ELSE 'equal' END AS distance_category,
       coalesce(planned_geodesic_km = 0, false) AS zero_planned_distance,
       coalesce(planned_same_address_nonzero_legs, 0) AS planned_same_address_nonzero_legs,
       coalesce(actual_same_address_nonzero_legs, 0) AS actual_same_address_nonzero_legs,
       coalesce(abs(signed_difference_km) >= 100, false) AS large_distance_gap,
       (distance_visit_count IS NULL OR planned_geodesic_km = 0
           OR planned_same_address_nonzero_legs > 0 OR actual_same_address_nonzero_legs > 0
           OR abs(signed_difference_km) >= 100) AS distance_review_flag,
       route.eligible_delivery_visit_count, route.late_delivery_visit_count,
       route.late_delivery_visit_count::numeric / nullif(route.eligible_delivery_visit_count, 0)
           AS late_delivery_rate,
       route.has_eligible_delivery, route.has_late_arrival, route.route_timing_span_over_1440
FROM reporting.route_sequence_deviation AS route
LEFT JOIN differences USING (route_id, import_id);

CREATE OR REPLACE VIEW reporting.route_distance_comparison AS
WITH cohorts AS (
    SELECT timing_cohort, distance.*
    FROM reporting.route_distance AS distance
    CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route_timing_span_over_1440
        THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
), summary AS (
    SELECT timing_cohort, country, country_name, route_size_band, address_sequence_status, distance_category,
           count(*) AS route_count, sum(visit_count) AS visit_count,
           count(*) FILTER (WHERE distance_review_flag) AS distance_review_route_count,
           count(*) FILTER (WHERE zero_planned_distance) AS zero_planned_route_count,
           count(distance_difference_pct) AS percent_difference_route_count,
           sum(planned_geodesic_km) AS total_planned_geodesic_km,
           sum(actual_geodesic_km) AS total_actual_geodesic_km,
           sum(signed_difference_km) AS total_signed_difference_km,
           sum(absolute_difference_km) AS total_absolute_difference_km,
           avg(distance_difference_pct) AS mean_distance_difference_pct,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY planned_geodesic_km) AS median_planned_geodesic_km,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY actual_geodesic_km) AS median_actual_geodesic_km,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY signed_difference_km) AS p05_signed_difference_km,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY signed_difference_km) AS median_signed_difference_km,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY signed_difference_km) AS p95_signed_difference_km,
           count(*) FILTER (WHERE has_eligible_delivery) AS eligible_route_count,
           count(*) FILTER (WHERE has_late_arrival) AS late_route_count,
           sum(eligible_delivery_visit_count) AS eligible_delivery_count,
           sum(late_delivery_visit_count) AS late_delivery_count
    FROM cohorts
    GROUP BY timing_cohort, CUBE((country, country_name), route_size_band, address_sequence_status, distance_category)
)
SELECT summary.*,
       late_route_count::numeric / nullif(eligible_route_count, 0) AS late_route_rate,
       late_delivery_count / nullif(eligible_delivery_count, 0) AS late_delivery_rate
FROM summary;

GRANT SELECT ON reporting.route_distance, reporting.route_distance_comparison TO p002_report;
COMMIT;

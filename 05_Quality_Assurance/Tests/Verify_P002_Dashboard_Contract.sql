\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;

DO $$
DECLARE
    observed bigint[];
BEGIN
    SELECT ARRAY[count(*), count(DISTINCT (import_id, worksheet_name, source_row_number)),
                 count(*) FILTER (WHERE route_id IS NULL)]
    INTO observed FROM reporting.dashboard_visit;
    IF observed IS DISTINCT FROM ARRAY[249231,249231,0]::bigint[] THEN
        RAISE EXCEPTION 'Dashboard visit grain mismatch: %', observed;
    END IF;
    SELECT ARRAY[count(*), count(DISTINCT (route_id,import_id)), sum(visit_count)::bigint]
    INTO observed FROM reporting.dashboard_route;
    IF observed IS DISTINCT FROM ARRAY[19647,19647,249231]::bigint[] OR
       (SELECT count(*) FROM reporting.dashboard_visit AS visit JOIN reporting.dashboard_route AS route
            USING (route_id, import_id)) <> 249231 THEN
        RAISE EXCEPTION 'Dashboard route grain or drill-through mismatch: %', observed;
    END IF;

    IF (SELECT count(*) FROM reporting.dashboard_overview) <> 3 OR EXISTS (
        SELECT FROM reporting.dashboard_overview AS overview
        FULL JOIN (VALUES
            ('full',249231,19647,213122,23718,19383,8387),
            ('span_at_most_1440',234689,18479,201796,21748,18238,7771),
            ('removed_over_1440',14542,1168,11326,1970,1145,616)
        ) AS expected(timing_cohort,visits,routes,deliveries,late_deliveries,eligible_routes,late_routes)
        USING (timing_cohort)
        WHERE (source_visit_count,route_count,eligible_delivery_count,late_count,eligible_route_count,late_route_count)
              IS DISTINCT FROM (visits,routes,deliveries,late_deliveries,eligible_routes,late_routes)
           OR early_count + in_window_count + late_count <> eligible_delivery_count
           OR late_delivery_rate IS DISTINCT FROM late_count::numeric / nullif(eligible_delivery_count,0)
           OR late_route_rate IS DISTINCT FROM late_route_count::numeric / nullif(eligible_route_count,0)
    ) OR NOT EXISTS (
        SELECT FROM reporting.dashboard_overview AS overview CROSS JOIN reporting.arrival_window_summary AS approved
        WHERE timing_cohort = 'full'
          AND (overview.early_count,overview.in_window_count,overview.median_late_minutes,overview.p90_late_minutes)
            IS NOT DISTINCT FROM (approved.early_count,approved.in_window_count,approved.median_late_minutes,approved.p90_late_minutes)
          AND changed_address_route_count = 14378 AND valid_sequence_route_count = 19647
          AND distance_review_route_count = 98
    ) THEN
        RAISE EXCEPTION 'Dashboard timing cohorts or baseline metrics mismatch';
    END IF;

    IF NOT EXISTS (
        WITH selected AS (
            SELECT count(*) AS routes, count(*) FILTER (WHERE has_eligible_delivery) AS eligible_routes,
                   count(*) FILTER (WHERE has_late_arrival) AS late_routes,
                   sum(eligible_delivery_visit_count) AS eligible_deliveries,
                   sum(late_delivery_visit_count) AS late_deliveries
            FROM reporting.dashboard_route
            WHERE country = 0 AND route_size_band = '11–20'
              AND address_sequence_status = 'changed' AND NOT route_timing_span_over_1440
        )
        SELECT FROM selected CROSS JOIN reporting.route_distance_comparison AS comparison
        WHERE comparison.timing_cohort = 'span_at_most_1440' AND comparison.country = 0
          AND comparison.route_size_band = '11–20' AND comparison.address_sequence_status = 'changed'
          AND comparison.distance_category IS NULL
          AND (routes,eligible_routes,late_routes,eligible_deliveries,late_deliveries) =
              (route_count,eligible_route_count,late_route_count,eligible_delivery_count,late_delivery_count)
    ) OR NOT EXISTS (
        SELECT FROM reporting.route_performance_standardized
        WHERE timing_cohort = 'full' AND supported_strata = 6 AND observed_strata = 8
          AND supported_pooled_eligible_routes = 17617 AND observed_pooled_eligible_routes = 19383
          AND round(route_gap_pp,2) = -0.15
    ) THEN
        RAISE EXCEPTION 'Scoped drill-down or fixed standardization mismatch';
    END IF;

    IF EXISTS (
        SELECT FROM (VALUES ('dashboard_visit'), ('dashboard_route'), ('dashboard_overview')) AS selected(name)
        WHERE NOT has_table_privilege('p002_report','reporting.' || name,'SELECT')
           OR has_table_privilege('p002_report','reporting.' || name,'INSERT, UPDATE, DELETE')
    ) OR has_schema_privilege('p002_report','core','USAGE') OR has_schema_privilege('p002_report','staging','USAGE') THEN
        RAISE EXCEPTION 'Unexpected dashboard grants';
    END IF;
END
$$;

SELECT timing_cohort, route_count, eligible_delivery_count, late_count, late_route_count
FROM reporting.dashboard_overview ORDER BY timing_cohort;
SELECT 'P002 dashboard data contract passed' AS result;
COMMIT;

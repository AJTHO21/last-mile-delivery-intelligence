\set ON_ERROR_STOP on
BEGIN READ ONLY;

DO $$
DECLARE
    failures bigint;
    baseline bigint[];
BEGIN
    WITH source_totals AS (
        SELECT visit.route_id, visit.import_id, count(*) AS visits,
               sum(source.distance_p::numeric) AS planned,
               sum(source.distance_a::numeric) AS actual,
               count(*) FILTER (WHERE visit.distance_p_km IS DISTINCT FROM source.distance_p::numeric
                                  OR visit.distance_a_km IS DISTINCT FROM source.distance_a::numeric) AS leg_errors,
               count(*) FILTER (WHERE visit.address_id = planned.address_id AND visit.distance_p_km <> 0) AS planned_flags,
               count(*) FILTER (WHERE visit.address_id = actual.address_id AND visit.distance_a_km <> 0) AS actual_flags,
               array_agg(visit.address_id ORDER BY visit.index_p) = array_agg(visit.address_id ORDER BY visit.index_a)
                   AS exact_address,
               count(*) FILTER (WHERE NOT visit.depot AND visit.delivery) AS eligible,
               count(*) FILTER (WHERE NOT visit.depot AND visit.delivery AND visit.arrived_minutes > visit.latest_minutes) AS late,
               max(greatest(visit.arrived_minutes, visit.earliest_minutes, visit.latest_minutes))
                   - min(least(visit.arrived_minutes, visit.earliest_minutes, visit.latest_minutes)) > 1440 AS timing_flag
        FROM core.visit
        JOIN staging.source_visit AS source USING (import_id, worksheet_name, source_row_number)
        LEFT JOIN core.visit AS planned ON planned.route_id = visit.route_id AND planned.index_p = visit.index_p - 1
        LEFT JOIN core.visit AS actual ON actual.route_id = visit.route_id AND actual.index_a = visit.index_a - 1
        GROUP BY visit.route_id, visit.import_id
    )
    SELECT count(*) INTO failures
    FROM reporting.route_distance AS distance
    FULL JOIN core.route AS route USING (route_id, import_id)
    LEFT JOIN source_totals AS expected USING (route_id, import_id)
    WHERE route.route_id IS NULL OR distance.route_id IS NULL OR expected.route_id IS NULL OR leg_errors <> 0
       OR (distance.country, visit_count, distance_visit_count, planned_geodesic_km, actual_geodesic_km,
           signed_difference_km, absolute_difference_km, distance_difference_pct, exact_address_match,
           planned_same_address_nonzero_legs, actual_same_address_nonzero_legs,
           eligible_delivery_visit_count, late_delivery_visit_count, has_eligible_delivery, has_late_arrival,
           late_delivery_rate, route_timing_span_over_1440, zero_planned_distance, large_distance_gap,
           distance_review_flag, distance_category)
       IS DISTINCT FROM
          (route.country, visits, visits, planned, actual, actual - planned, abs(actual - planned),
           100 * (actual - planned) / nullif(planned,0), exact_address, planned_flags, actual_flags,
           eligible, late, eligible > 0, late > 0, late::numeric / nullif(eligible,0), timing_flag,
           planned = 0, abs(actual - planned) >= 100,
           planned = 0 OR planned_flags > 0 OR actual_flags > 0 OR abs(actual - planned) >= 100,
           CASE WHEN abs(actual - planned) <= 0.000000001 THEN 'equal'
                WHEN actual < planned THEN 'shorter' ELSE 'longer' END);

    IF failures <> 0 THEN
        RAISE EXCEPTION 'Route, leg, timing or arrival parity failed on % rows', failures;
    END IF;

    SELECT ARRAY[count(*), count(DISTINCT route_id), sum(distance_visit_count)::bigint,
                 count(*) FILTER (WHERE distance_category = 'shorter'),
                 count(*) FILTER (WHERE distance_category = 'equal'),
                 count(*) FILTER (WHERE distance_category = 'longer'),
                 count(*) FILTER (WHERE zero_planned_distance AND distance_difference_pct IS NULL),
                 count(distance_difference_pct),
                 sum(planned_same_address_nonzero_legs)::bigint, sum(actual_same_address_nonzero_legs)::bigint,
                 count(*) FILTER (WHERE route_timing_span_over_1440),
                 sum(eligible_delivery_visit_count) FILTER (WHERE route_timing_span_over_1440)::bigint,
                 sum(late_delivery_visit_count) FILTER (WHERE route_timing_span_over_1440)::bigint]
    INTO baseline FROM reporting.route_distance;

    IF baseline IS DISTINCT FROM ARRAY[19647,19647,249231,7386,5291,6970,1,19646,0,1,1168,11326,1970]::bigint[]
       OR baseline[1] <> (SELECT count(*) FROM core.route)
       OR baseline[3] <> (SELECT count(*) FROM core.visit)
       OR NOT EXISTS (SELECT 1 FROM reporting.route_distance
                      WHERE route_id = 7545 AND actual_same_address_nonzero_legs = 1 AND distance_review_flag) THEN
        RAISE EXCEPTION 'Unexpected Phase 0 totals or anomaly counts: %', baseline;
    END IF;

    WITH detail AS MATERIALIZED (SELECT * FROM reporting.route_distance),
    expanded AS (
        SELECT timing_cohort,
               CASE WHEN mask & 1 = 0 THEN country END AS country,
               CASE WHEN mask & 2 = 0 THEN route_size_band END AS route_size_band,
               CASE WHEN mask & 4 = 0 THEN address_sequence_status END AS address_sequence_status,
               CASE WHEN mask & 8 = 0 THEN distance_category END AS distance_category,
               visit_count, distance_review_flag, zero_planned_distance, distance_difference_pct,
               planned_geodesic_km, actual_geodesic_km, signed_difference_km, absolute_difference_km,
               has_eligible_delivery, has_late_arrival, eligible_delivery_visit_count, late_delivery_visit_count
        FROM detail
        CROSS JOIN generate_series(0,15) AS mask
        CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route_timing_span_over_1440
            THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
    ), expected AS (
        SELECT timing_cohort, country, route_size_band, address_sequence_status, distance_category,
               count(*), sum(visit_count), count(*) FILTER (WHERE distance_review_flag),
               count(*) FILTER (WHERE zero_planned_distance), count(distance_difference_pct),
               sum(planned_geodesic_km), sum(actual_geodesic_km),
               sum(signed_difference_km), sum(absolute_difference_km),
               count(*) FILTER (WHERE has_eligible_delivery), count(*) FILTER (WHERE has_late_arrival),
               sum(eligible_delivery_visit_count), sum(late_delivery_visit_count)
        FROM expanded
        GROUP BY timing_cohort, country, route_size_band, address_sequence_status, distance_category
    ), observed AS MATERIALIZED (
        SELECT timing_cohort, country, route_size_band, address_sequence_status, distance_category,
               route_count, visit_count, distance_review_route_count, zero_planned_route_count, percent_difference_route_count,
               total_planned_geodesic_km, total_actual_geodesic_km,
               total_signed_difference_km, total_absolute_difference_km,
               eligible_route_count, late_route_count, eligible_delivery_count, late_delivery_count
        FROM reporting.route_distance_comparison
    )
    SELECT count(*) INTO failures FROM (
        (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
        UNION ALL (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
    ) AS differences;

    IF failures <> 0 OR EXISTS (
        SELECT 1 FROM reporting.route_distance_comparison
        WHERE late_delivery_rate IS DISTINCT FROM late_delivery_count / nullif(eligible_delivery_count,0)
           OR late_route_rate IS DISTINCT FROM late_route_count::numeric / nullif(eligible_route_count,0)
    ) THEN
        RAISE EXCEPTION 'Distance grouping or denominator reconciliation failed';
    END IF;

    IF NOT has_table_privilege('p002_report', 'reporting.route_distance', 'SELECT')
       OR NOT has_table_privilege('p002_report', 'reporting.route_distance_comparison', 'SELECT')
       OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE') THEN
        RAISE EXCEPTION 'Unexpected reporting privileges';
    END IF;
END
$$;

SELECT row_to_json(summary) AS comparison FROM reporting.route_distance_comparison AS summary
WHERE (country IS NULL AND route_size_band IS NULL AND address_sequence_status IS NULL)
   OR (distance_category IS NULL AND timing_cohort = 'full'
       AND num_nonnulls(country, route_size_band, address_sequence_status) = 1);
SELECT row_to_json(flags) AS flags FROM (
    SELECT count(*) FILTER (WHERE large_distance_gap) AS large_gaps,
           count(*) FILTER (WHERE distance_review_flag) AS flagged_routes,
           min(signed_difference_km) AS min_gap_km, max(signed_difference_km) AS max_gap_km
    FROM reporting.route_distance
) AS flags;
ROLLBACK;

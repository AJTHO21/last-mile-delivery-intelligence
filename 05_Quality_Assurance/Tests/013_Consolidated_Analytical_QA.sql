\set ON_ERROR_STOP on
\ir Verify_P002_Arrival_Window.sql
\ir Verify_P002_Route_Sequence.sql
\ir Verify_P002_Route_Performance.sql
\ir Verify_P002_Route_Distance.sql

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;

DO $$
DECLARE
    mismatches bigint;
    counts bigint[];
    statistics numeric[];
BEGIN
    IF current_database() <> 'p002_last_mile' OR current_user <> 'p002_dev' THEN
        RAISE EXCEPTION 'Run consolidated QA as p002_dev in p002_last_mile';
    END IF;
    IF (SELECT count(*) FROM staging.source_import) <> 1 OR NOT EXISTS (
        SELECT FROM staging.source_import
        WHERE sha256 = '8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00'
          AND source_doi = '10.17632/kkwgfvmtxn.1' AND source_version = 1
          AND source_filename = 'routes_performance.xlsx'
    ) THEN
        RAISE EXCEPTION 'Source import identity mismatch';
    END IF;

    SELECT count(*) INTO mismatches
    FROM staging.source_visit AS source
    FULL JOIN core.visit AS visit USING (import_id, worksheet_name, source_row_number)
    LEFT JOIN core.route AS route ON (visit.route_id, visit.import_id) = (route.route_id, route.import_id)
    WHERE source.source_row_number IS NULL OR visit.source_row_number IS NULL OR route.route_id IS NULL
       OR (visit.route_id, route.driver_id, route.country, visit.stop_id, visit.address_id,
           visit.week_id, visit.day_of_week, visit.index_p, visit.index_a, visit.arrived_minutes,
           visit.earliest_minutes, visit.latest_minutes, visit.distance_p_km, visit.distance_a_km,
           visit.depot, visit.delivery)
          IS DISTINCT FROM
          (source.route_id::integer, source.driver_id::integer, source.country::smallint,
           source.stop_id::integer, source.address_id::integer, source.week_id::integer, source.day_of_week,
           source.index_p::integer, source.index_a::integer, source.arrived_time::numeric,
           source.earliest_time::numeric, source.latest_time::numeric, source.distance_p::numeric,
           source.distance_a::numeric, source.depot::boolean, source.delivery::boolean);
    IF mismatches <> 0 OR (SELECT count(*) FROM staging.source_visit) <> 249231
       OR EXISTS (SELECT FROM staging.source_visit WHERE worksheet_name <> 'Sheet1'
                  OR source_row_number NOT BETWEEN 2 AND 249232) THEN
        RAISE EXCEPTION 'Workbook lineage or typed field mismatch: %', mismatches;
    END IF;

    WITH visits AS MATERIALIZED (
        SELECT *, delivery AND NOT depot AS eligible
        FROM core.visit
    ), routes AS (
        SELECT route_id, count(*) AS n, bool_or(index_p <> index_a) AS changed_visit,
               count(*) FILTER (WHERE index_p <> index_a) AS moved,
               bool_or(eligible) AS eligible,
               bool_or(eligible AND arrived_minutes > latest_minutes) AS late,
               sum(distance_p_km) AS planned, sum(distance_a_km) AS actual,
               max(greatest(arrived_minutes, earliest_minutes, latest_minutes))
                 - min(least(arrived_minutes, earliest_minutes, latest_minutes)) > 1440 AS long_span
        FROM visits GROUP BY route_id
    ), arrivals AS (
        SELECT count(*) FILTER (WHERE eligible) AS eligible,
               count(*) FILTER (WHERE eligible AND arrived_minutes > latest_minutes) AS late,
               count(*) FILTER (WHERE eligible AND arrived_minutes < earliest_minutes) AS early,
               count(*) FILTER (WHERE eligible AND arrived_minutes BETWEEN earliest_minutes AND latest_minutes) AS inside,
               percentile_cont(ARRAY[0.5,0.9]) WITHIN GROUP (ORDER BY arrived_minutes - latest_minutes)
                   FILTER (WHERE eligible AND arrived_minutes > latest_minutes) AS late_quantiles
        FROM visits
    ), distance AS (
        SELECT count(*) AS routes, sum(n)::bigint AS visits,
               count(*) FILTER (WHERE changed_visit) AS changed,
               sum(moved)::bigint AS moved,
               count(*) FILTER (WHERE eligible) AS eligible,
               count(*) FILTER (WHERE late) AS late,
               count(*) FILTER (WHERE actual - planned < -1e-9) AS shorter,
               count(*) FILTER (WHERE abs(actual - planned) <= 1e-9) AS equal,
               count(*) FILTER (WHERE actual - planned > 1e-9) AS longer,
               count(*) FILTER (WHERE long_span) AS long_spans,
               sum(planned) AS planned, sum(actual) AS actual,
               percentile_cont(ARRAY[0.05,0.5,0.95]) WITHIN GROUP (ORDER BY actual - planned) AS gap_quantiles
        FROM routes
    ), review AS (
        SELECT count(*) AS n FROM routes
        WHERE planned = 0 OR abs(actual - planned) >= 100 OR EXISTS (
            SELECT FROM core.visit AS visit
            JOIN core.visit AS prior ON prior.route_id = visit.route_id AND prior.address_id = visit.address_id
                AND ((prior.index_p = visit.index_p - 1 AND visit.distance_p_km <> 0)
                  OR (prior.index_a = visit.index_a - 1 AND visit.distance_a_km <> 0))
            WHERE visit.route_id = routes.route_id
        )
    )
    SELECT ARRAY[visits, routes, arrivals.eligible, arrivals.late, early, inside,
                 changed, moved, distance.eligible, distance.late, shorter, equal, longer, review.n, long_spans],
           ARRAY[round(planned,2), round(actual,2), round(gap_quantiles[1]::numeric,2),
                 round(gap_quantiles[2]::numeric,2), round(gap_quantiles[3]::numeric,2),
                 round(late_quantiles[1]::numeric,2), round(late_quantiles[2]::numeric,2)]
    INTO counts, statistics FROM distance CROSS JOIN arrivals CROSS JOIN review;

    IF counts IS DISTINCT FROM ARRAY[249231,19647,213122,23718,24252,165152,15067,124310,
         19383,8387,7386,5291,6970,98,1168]::bigint[] THEN
        RAISE EXCEPTION 'Independent KPI counts differ: %', counts;
    END IF;
    IF statistics IS DISTINCT FROM ARRAY[1260561.50,1241690.34,-17.77,0,11.60,47.94,206.09]::numeric[]
       OR NOT EXISTS (
           SELECT FROM reporting.route_distance_comparison
           WHERE timing_cohort = 'full' AND num_nonnulls(country,route_size_band,address_sequence_status,distance_category) = 0
             AND ARRAY[round(total_planned_geodesic_km,2), round(total_actual_geodesic_km,2),
                       round(p05_signed_difference_km::numeric,2), round(median_signed_difference_km::numeric,2),
                       round(p95_signed_difference_km::numeric,2)] = statistics[1:5]
       ) THEN
        RAISE EXCEPTION 'Independent distance or lateness statistics differ: %', statistics;
    END IF;
    RAISE NOTICE 'Independent counts: %', counts;
    RAISE NOTICE 'Independent planned/actual km, gap P05/P50/P95, late P50/P90: %', statistics;
END
$$;

DO $$
DECLARE
    discrepancies bigint;
BEGIN
    -- Derive support and weights from typed visits without using reporting inputs.
    WITH routes AS (
        SELECT route_id, route.country, count(*) AS size,
               array_agg(address_id ORDER BY index_p) <> array_agg(address_id ORDER BY index_a) AS changed,
               count(*) FILTER (WHERE NOT depot AND delivery) AS eligible,
               count(*) FILTER (WHERE NOT depot AND delivery AND arrived_minutes > latest_minutes) AS late,
               max(greatest(arrived_minutes, earliest_minutes, latest_minutes))
                 - min(least(arrived_minutes, earliest_minutes, latest_minutes)) <= 1440 AS retained
        FROM core.visit JOIN core.route AS route USING (route_id, import_id)
        GROUP BY route_id, route.country
    ), strata AS (
        SELECT timing_cohort, country,
               CASE WHEN size <= 5 THEN '1–5' WHEN size <= 10 THEN '6–10'
                    WHEN size <= 20 THEN '11–20' ELSE '21+' END AS route_size_band,
               count(*) FILTER (WHERE changed AND eligible > 0) AS ec,
               count(*) FILTER (WHERE NOT changed AND eligible > 0) AS eu,
               count(*) FILTER (WHERE changed AND late > 0) AS lc,
               count(*) FILTER (WHERE NOT changed AND late > 0) AS lu,
               sum(eligible) FILTER (WHERE changed) AS vc,
               sum(eligible) FILTER (WHERE NOT changed) AS vu,
               sum(late) FILTER (WHERE changed) AS dc,
               sum(late) FILTER (WHERE NOT changed) AS du
        FROM routes CROSS JOIN (VALUES ('full'), ('span_at_most_1440')) AS cohort(timing_cohort)
        WHERE timing_cohort = 'full' OR retained
        GROUP BY 1,2,3
    ), support AS (
        SELECT *, least(ec,eu) >= 50 AND least(vc,vu) >= 100 AS supported FROM strata
    ), weighted AS (
        SELECT *, CASE WHEN supported THEN (ec + eu)::numeric /
            sum(ec + eu) FILTER (WHERE supported) OVER (PARTITION BY timing_cohort) END AS weight
        FROM support
    ), statistics AS (
        SELECT timing_cohort, count(*) AS observed, count(*) FILTER (WHERE supported) AS supported,
               sum(ec+eu) AS population, sum(ec+eu) FILTER (WHERE supported) AS supported_population,
               sum(weight * lc::numeric / nullif(ec,0)) AS rc,
               sum(weight * lu::numeric / nullif(eu,0)) AS ru,
               sum(weight * dc / nullif(vc,0)) AS vc_rate,
               sum(weight * du / nullif(vu,0)) AS vu_rate
        FROM weighted GROUP BY timing_cohort
    )
    SELECT (SELECT count(*) FROM weighted
            FULL JOIN reporting.route_performance_standardization_strata AS observed
               USING (timing_cohort,country,route_size_band)
            WHERE (ec,eu,lc,lu,vc,vu,dc,du,supported,ec+eu) IS DISTINCT FROM
               (changed_eligible_route_count,unchanged_eligible_route_count,changed_late_route_count,
                unchanged_late_route_count,changed_eligible_delivery_count,unchanged_eligible_delivery_count,
                changed_late_delivery_count,unchanged_late_delivery_count,adequate_support,pooled_eligible_routes)
               OR (weight IS NULL) <> (common_weight IS NULL)
               OR abs(weight - common_weight) > 1e-12)
         + (SELECT count(*) FROM statistics
            FULL JOIN reporting.route_performance_standardized AS actual USING (timing_cohort)
            WHERE (observed, supported, population, supported_population) IS DISTINCT FROM
                (observed_strata, supported_strata, observed_pooled_eligible_routes, supported_pooled_eligible_routes)
               OR coalesce(abs(rc-changed_route_rate),1) > 1e-12
               OR coalesce(abs(ru-unchanged_route_rate),1) > 1e-12
               OR coalesce(abs(vc_rate-changed_delivery_rate),1) > 1e-12
               OR coalesce(abs(vu_rate-unchanged_delivery_rate),1) > 1e-12)
    INTO discrepancies;
    IF discrepancies <> 0 THEN
        RAISE EXCEPTION 'Independent country/size support or weighting differs: %', discrepancies;
    END IF;
END
$$;

SELECT timing_cohort, supported_strata, observed_strata, supported_pooled_eligible_routes,
       observed_pooled_eligible_routes, round(route_gap_pp,2) AS standardized_route_gap_pp,
       round(delivery_gap_pp,2) AS standardized_delivery_gap_pp
FROM reporting.route_performance_standardized ORDER BY timing_cohort;
SELECT 'P002 consolidated analytical QA passed' AS result;
COMMIT;

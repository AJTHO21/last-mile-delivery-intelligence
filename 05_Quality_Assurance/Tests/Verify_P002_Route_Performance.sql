\set ON_ERROR_STOP on
BEGIN READ ONLY;

DO $$
DECLARE
    discrepancies integer;
    baseline bigint[];
BEGIN
    WITH expected_routes AS (
        SELECT route.route_id, route.country, count(*) AS route_size,
               array_agg(address_id ORDER BY index_p) <> array_agg(address_id ORDER BY index_a) AS changed,
               count(*) FILTER (WHERE NOT depot AND delivery) AS eligible,
               count(*) FILTER (WHERE NOT depot AND delivery AND arrived_minutes > latest_minutes) AS late,
               max(greatest(arrived_minutes, earliest_minutes, latest_minutes))
                 - min(least(arrived_minutes, earliest_minutes, latest_minutes)) > 1440 AS flagged
        FROM core.visit JOIN core.route AS route USING (route_id, import_id)
        GROUP BY route.route_id, route.country
    ), expected_bands AS (
        SELECT *, CASE WHEN route_size <= 5 THEN '1–5' WHEN route_size <= 10 THEN '6–10'
                       WHEN route_size <= 20 THEN '11–20' ELSE '21+' END AS band
        FROM expected_routes
    ), expected_cohorts AS (
        SELECT expected_bands.*, timing_cohort
        FROM expected_bands
        CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN flagged THEN 'removed_over_1440'
             ELSE 'span_at_most_1440' END)) AS cohorts(timing_cohort)
    ), observed AS (
        SELECT timing_cohort, country, route_size_band AS band, comparison.changed,
               comparison.route_count, comparison.eligible_route_count, comparison.late_route_count,
               comparison.eligible_delivery_count, comparison.late_delivery_count
        FROM reporting.route_performance_comparison
        CROSS JOIN LATERAL (VALUES
           (true, changed_route_count, changed_eligible_route_count, changed_late_route_count,
                  changed_eligible_delivery_count, changed_late_delivery_count),
           (false, unchanged_route_count, unchanged_eligible_route_count, unchanged_late_route_count,
                   unchanged_eligible_delivery_count, unchanged_late_delivery_count)
        ) AS comparison(changed, route_count, eligible_route_count, late_route_count,
                         eligible_delivery_count, late_delivery_count)
        WHERE comparison.route_count > 0
    ), expected AS (
        SELECT timing_cohort, country, band, changed, count(*),
               count(*) FILTER (WHERE eligible > 0), count(*) FILTER (WHERE late > 0),
               sum(eligible)::bigint, sum(late)::bigint
        FROM expected_cohorts
        GROUP BY timing_cohort, changed, GROUPING SETS ((), (country), (band), (country, band))
    )
    SELECT count(*) INTO discrepancies FROM (
        (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
        UNION ALL (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
    ) AS differences;

    IF discrepancies <> 0 THEN
        RAISE EXCEPTION 'Route, delivery, or country/size reconciliation failed';
    END IF;

    SELECT ARRAY[
        sum(changed_route_count + unchanged_route_count) FILTER (WHERE timing_cohort = 'full')::bigint,
        sum(changed_eligible_route_count + unchanged_eligible_route_count) FILTER (WHERE timing_cohort = 'full')::bigint,
        sum(changed_late_route_count + unchanged_late_route_count) FILTER (WHERE timing_cohort = 'full')::bigint,
        sum(changed_eligible_delivery_count + unchanged_eligible_delivery_count) FILTER (WHERE timing_cohort = 'full')::bigint,
        sum(changed_late_delivery_count + unchanged_late_delivery_count) FILTER (WHERE timing_cohort = 'full')::bigint,
        sum(changed_route_count + unchanged_route_count) FILTER (WHERE timing_cohort = 'removed_over_1440')::bigint,
        sum(changed_eligible_delivery_count + unchanged_eligible_delivery_count) FILTER (WHERE timing_cohort = 'removed_over_1440')::bigint,
        sum(changed_late_delivery_count + unchanged_late_delivery_count) FILTER (WHERE timing_cohort = 'removed_over_1440')::bigint
    ] INTO baseline
    FROM reporting.route_performance_comparison WHERE country IS NULL AND route_size_band IS NULL;

    IF baseline IS DISTINCT FROM ARRAY[19647,19383,8387,213122,23718,1168,11326,1970]::bigint[]
       OR baseline[1] <> (SELECT count(*) FROM core.route)
       OR EXISTS (
           SELECT 1 FROM reporting.route_performance_comparison
           WHERE unverified_route_count <> 0
              OR (changed_route_rate, unchanged_route_rate, changed_delivery_rate, unchanged_delivery_rate)
                 IS DISTINCT FROM (changed_late_route_count::numeric / nullif(changed_eligible_route_count,0),
                     unchanged_late_route_count::numeric / nullif(unchanged_eligible_route_count,0),
                     changed_late_delivery_count::numeric / nullif(changed_eligible_delivery_count,0),
                     unchanged_late_delivery_count::numeric / nullif(unchanged_eligible_delivery_count,0))
              OR route_gap_pp IS DISTINCT FROM 100 * (changed_route_rate - unchanged_route_rate)
              OR delivery_gap_pp IS DISTINCT FROM 100 * (changed_delivery_rate - unchanged_delivery_rate)
       ) THEN
        RAISE EXCEPTION 'Baseline, sensitivity, or denominator QA failed: %', baseline;
    END IF;

    WITH strata AS MATERIALIZED (SELECT * FROM reporting.route_performance_standardization_strata),
    independent AS (
        SELECT timing_cohort, count(*) FILTER (WHERE adequate_support) AS supported,
               sum(common_weight) AS weight_total,
               sum(pooled_eligible_routes) FILTER (WHERE adequate_support) AS pooled,
               sum(pooled_eligible_routes * changed_route_rate) FILTER (WHERE adequate_support) AS changed_route,
               sum(pooled_eligible_routes * unchanged_route_rate) FILTER (WHERE adequate_support) AS unchanged_route,
               sum(pooled_eligible_routes * changed_delivery_rate) FILTER (WHERE adequate_support) AS changed_delivery,
               sum(pooled_eligible_routes * unchanged_delivery_rate) FILTER (WHERE adequate_support) AS unchanged_delivery
        FROM strata GROUP BY timing_cohort
    )
    SELECT count(*) INTO discrepancies
    FROM independent FULL JOIN reporting.route_performance_standardized AS result USING (timing_cohort)
    WHERE independent.supported IS DISTINCT FROM result.supported_strata
       OR independent.pooled IS DISTINCT FROM result.supported_pooled_eligible_routes
       OR abs(weight_total - 1) > 1e-12
       OR abs(result.changed_route_rate - changed_route / pooled) > 1e-12
       OR abs(result.unchanged_route_rate - unchanged_route / pooled) > 1e-12
       OR abs(result.changed_delivery_rate - changed_delivery / pooled) > 1e-12
       OR abs(result.unchanged_delivery_rate - unchanged_delivery / pooled) > 1e-12
       OR result.route_gap_pp IS DISTINCT FROM 100 * (result.changed_route_rate - result.unchanged_route_rate)
       OR result.delivery_gap_pp IS DISTINCT FROM 100 * (result.changed_delivery_rate - result.unchanged_delivery_rate)
       OR EXISTS (
           SELECT 1 FROM strata WHERE adequate_support IS DISTINCT FROM
               (least(changed_eligible_route_count, unchanged_eligible_route_count) >= 50
                AND least(changed_eligible_delivery_count, unchanged_eligible_delivery_count) >= 100)
               OR (common_weight IS NULL) = adequate_support
       );

    IF discrepancies <> 0 THEN
        RAISE EXCEPTION 'Standardization QA failed';
    END IF;

    WITH totals AS (
        SELECT timing_cohort, array[sum(visit_count), sum(eligible_delivery_count), sum(late_delivery_count)] AS counts
        FROM reporting.visit_displacement_lateness GROUP BY timing_cohort
    )
    SELECT count(*) INTO discrepancies
    FROM totals FULL JOIN (VALUES ('full', ARRAY[249231,213122,23718]),
        ('span_at_most_1440', ARRAY[(SELECT count(*)::integer FROM reporting.visit_arrival_window
                                   WHERE NOT route_timing_span_over_1440),201796,21748]),
        ('removed_over_1440', ARRAY[(SELECT count(*)::integer FROM reporting.visit_arrival_window
                                   WHERE route_timing_span_over_1440),11326,1970])) AS expected(timing_cohort, counts)
        USING (timing_cohort)
    WHERE totals.counts IS DISTINCT FROM expected.counts::numeric[];

    IF discrepancies <> 0 OR NOT EXISTS (
        SELECT 1 FROM reporting.visit_displacement_lateness WHERE timing_cohort = 'full'
            AND address_status = 'unchanged' AND visit_order_status = 'changed_visit_order' AND displacement_band <> '0'
    ) OR EXISTS (
        SELECT 1 FROM reporting.visit_displacement_lateness
        WHERE (visit_order_status = 'exact_visit_order' AND displacement_band <> '0')
           OR late_delivery_rate IS DISTINCT FROM late_delivery_count::numeric / nullif(eligible_delivery_count,0)
           OR late_delivery_count > eligible_delivery_count OR eligible_delivery_count > visit_count
    ) THEN
        RAISE EXCEPTION 'Displacement visit grain or reconciliation failed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM (VALUES ('route_performance_comparison'), ('route_performance_standardization_strata'),
                              ('route_performance_standardized'), ('visit_displacement_lateness')) AS views(name)
        WHERE NOT has_table_privilege('p002_report', 'reporting.' || name, 'SELECT')
    ) OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE')
      OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE') THEN
        RAISE EXCEPTION 'Unexpected reporting privileges';
    END IF;
END
$$;

SELECT row_to_json(comparison) AS comparison FROM reporting.route_performance_comparison AS comparison;
SELECT row_to_json(stratum) AS support FROM reporting.route_performance_standardization_strata AS stratum;
SELECT row_to_json(standardized) AS standardized FROM reporting.route_performance_standardized AS standardized;
SELECT row_to_json(displacement) AS displacement FROM reporting.visit_displacement_lateness AS displacement;
ROLLBACK;

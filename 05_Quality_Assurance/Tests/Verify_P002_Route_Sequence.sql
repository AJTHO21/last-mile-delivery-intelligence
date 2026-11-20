\set ON_ERROR_STOP on
BEGIN READ ONLY;

DO $$
DECLARE
    route_metrics bigint[];
    detail_metrics bigint[];
    cohort_metrics bigint[];
BEGIN
    WITH detail AS MATERIALIZED (SELECT * FROM reporting.visit_sequence_deviation)
    SELECT ARRAY[count(*), count(DISTINCT (detail.route_id, detail.index_p)), count(DISTINCT (detail.route_id, detail.index_a)),
                 count(*) FILTER (WHERE moved_visit),
                 count(*) FILTER (WHERE (moved_visit, absolute_position_displacement)
                     IS DISTINCT FROM (detail.index_p <> detail.index_a, abs(detail.index_p - detail.index_a))),
                 count(*) FILTER (WHERE
                      planned_predecessor_index_p IS DISTINCT FROM planned.index_p
                      OR actual_predecessor_index_p IS DISTINCT FROM actual.index_p),
                 count(*) FILTER (WHERE
                     (detail.import_id, detail.worksheet_name, detail.source_row_number, detail.stop_id,
                      detail.address_id, detail.depot, detail.index_a)
                      IS DISTINCT FROM
                     (source.import_id, source.worksheet_name, source.source_row_number, source.stop_id,
                      source.address_id, source.depot, source.index_a))]
    INTO detail_metrics
    FROM detail
    LEFT JOIN core.visit AS source USING (route_id, index_p)
    LEFT JOIN core.visit AS planned ON planned.route_id = detail.route_id AND planned.index_p = detail.index_p - 1
    LEFT JOIN core.visit AS actual ON actual.route_id = detail.route_id AND actual.index_a = detail.index_a - 1;

    IF detail_metrics IS DISTINCT FROM ARRAY[249231,249231,249231,124310,0,0,0]::bigint[]
       OR detail_metrics[1] <> (SELECT count(*) FROM core.visit) THEN
        RAISE EXCEPTION 'Unexpected visit grain, lineage, or displacement: %', detail_metrics;
    END IF;

    WITH routes AS MATERIALIZED (SELECT * FROM reporting.route_sequence_deviation),
    source_counts AS (
        SELECT route_id, import_id, count(*) AS visits,
               count(*) FILTER (WHERE NOT depot AND delivery) AS eligible,
               count(*) FILTER (WHERE NOT depot AND delivery AND arrived_minutes > latest_minutes) AS late,
               count(DISTINCT stop_id) AS distinct_stops,
               count(DISTINCT address_id) AS distinct_addresses,
               array_agg(index_a ORDER BY index_p) AS actual_indices_in_planned_order,
               array_agg(index_p ORDER BY index_a) AS actual_sequence,
               array_agg(address_id ORDER BY index_p) AS planned_addresses,
               array_agg(address_id ORDER BY index_a) AS actual_addresses,
               sum(abs(index_a - index_p)) AS shift_total
        FROM core.visit GROUP BY route_id, import_id
    )
    SELECT ARRAY[count(*), count(DISTINCT routes.route_id),
                 count(*) FILTER (WHERE exact_visit_match),
                 count(*) FILTER (WHERE exact_address_match),
                 count(*) FILTER (WHERE NOT exact_visit_match),
                 sum(moved_visit_count)::bigint,
                 count(*) FILTER (WHERE has_eligible_delivery),
                 count(*) FILTER (WHERE has_late_arrival),
                 count(*) FILTER (WHERE exact_address_match AND NOT exact_visit_match),
                 count(*) FILTER (WHERE distinct_stops < visits),
                 count(*) FILTER (WHERE distinct_addresses < visits),
                 count(*) FILTER (WHERE NOT valid_sequence OR
                      (routes.visit_count, eligible_delivery_visit_count, late_delivery_visit_count,
                       planned_address_order, actual_address_order, cardinality(planned_visit_order),
                       actual_visit_order, exact_visit_match, exact_address_match,
                       total_absolute_position_displacement, has_eligible_delivery, has_late_arrival,
                       routes.country, routes.route_size_band)
                      IS DISTINCT FROM
                      (visits, eligible, late, planned_addresses, actual_addresses, visits::integer,
                       actual_sequence, planned_visit_order = actual_indices_in_planned_order,
                       planned_addresses = actual_addresses, shift_total, eligible > 0, late > 0,
                       parent.country, CASE WHEN visits <= 5 THEN '1–5' WHEN visits <= 10 THEN '6–10'
                                            WHEN visits <= 20 THEN '11–20' ELSE '21+' END))]
    INTO route_metrics
    FROM routes
    LEFT JOIN source_counts USING (route_id, import_id)
    LEFT JOIN core.route AS parent USING (route_id, import_id);

    IF route_metrics IS DISTINCT FROM ARRAY[19647,19647,4580,5269,15067,124310,19383,8387,689,6622,10961,0]::bigint[]
       OR route_metrics[1] <> (SELECT count(*) FROM core.route) THEN
        RAISE EXCEPTION 'Unexpected route QA counts: %', route_metrics;
    END IF;

    WITH summary AS MATERIALIZED (SELECT * FROM reporting.route_sequence_lateness_summary),
    overall AS (SELECT * FROM summary WHERE country IS NULL AND route_size_band IS NULL),
    fully_grouped AS (
        SELECT sum(route_count)::bigint AS routes, sum(eligible_route_count)::bigint AS eligible,
               sum(late_route_count)::bigint AS late
        FROM summary WHERE country IS NOT NULL AND route_size_band IS NOT NULL
                           AND address_sequence_status <> 'all'
    )
    SELECT ARRAY[
        (SELECT eligible_route_count FROM overall WHERE address_sequence_status = 'unchanged'),
        (SELECT late_route_count FROM overall WHERE address_sequence_status = 'unchanged'),
        (SELECT eligible_route_count FROM overall WHERE address_sequence_status = 'changed'),
        (SELECT late_route_count FROM overall WHERE address_sequence_status = 'changed'),
        (SELECT route_count FROM overall WHERE address_sequence_status = 'all'),
        (SELECT eligible_route_count FROM overall WHERE address_sequence_status = 'all'),
        (SELECT late_route_count FROM overall WHERE address_sequence_status = 'all'),
        routes, eligible, late,
        (SELECT count(*) FROM summary WHERE late_route_count > eligible_route_count
               OR eligible_route_count > route_count
               OR late_route_rate IS DISTINCT FROM late_route_count::numeric / nullif(eligible_route_count, 0))
    ]
    INTO cohort_metrics FROM fully_grouped;

    IF cohort_metrics IS DISTINCT FROM ARRAY[5119,1862,14264,6525,19647,19383,8387,19647,19383,8387,0]::bigint[] THEN
        RAISE EXCEPTION 'Unexpected cohort reconciliation: %', cohort_metrics;
    END IF;

    IF NOT has_table_privilege('p002_report', 'reporting.visit_sequence_deviation', 'SELECT')
       OR NOT has_table_privilege('p002_report', 'reporting.route_sequence_deviation', 'SELECT')
       OR NOT has_table_privilege('p002_report', 'reporting.route_sequence_lateness_summary', 'SELECT')
       OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE') THEN
        RAISE EXCEPTION 'Unexpected reporting privileges';
    END IF;
END
$$;

SELECT country_name, route_size_band, address_sequence_status, route_count,
       eligible_route_count, late_route_count, round(100 * late_route_rate, 2) AS late_route_pct
FROM reporting.route_sequence_lateness_summary
WHERE country IS NULL OR route_size_band IS NULL
ORDER BY country NULLS FIRST, route_size_band NULLS FIRST, address_sequence_status;
ROLLBACK;

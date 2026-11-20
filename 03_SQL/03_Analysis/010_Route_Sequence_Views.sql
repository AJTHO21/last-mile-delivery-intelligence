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

CREATE OR REPLACE VIEW reporting.visit_sequence_deviation AS
SELECT route_id, import_id, worksheet_name, source_row_number,
       index_p, index_a, stop_id, address_id, depot,
       index_p <> index_a AS moved_visit,
       abs(index_a - index_p) AS absolute_position_displacement,
       lag(index_p) OVER planned AS planned_predecessor_index_p,
       lag(index_p) OVER actual AS actual_predecessor_index_p
FROM core.visit
WINDOW planned AS (PARTITION BY route_id, import_id ORDER BY index_p),
       actual AS (PARTITION BY route_id, import_id ORDER BY index_a);

CREATE OR REPLACE VIEW reporting.route_sequence_deviation AS
WITH sequences AS (
    SELECT route_id, import_id, count(*) AS visit_count,
           count(*) FILTER (WHERE moved_visit) AS moved_visit_count,
           sum(absolute_position_displacement) AS total_absolute_position_displacement,
           avg(absolute_position_displacement) AS mean_absolute_position_displacement,
           max(absolute_position_displacement) AS max_absolute_position_displacement,
           min(index_p) = 0 AND max(index_p) = count(*) - 1
           AND min(index_a) = 0 AND max(index_a) = count(*) - 1 AS valid_sequence,
           array_agg(index_p ORDER BY index_p) AS planned_visit_order,
           array_agg(index_p ORDER BY index_a) AS actual_visit_order,
           array_agg(address_id ORDER BY index_p) AS planned_address_order,
           array_agg(address_id ORDER BY index_a) AS actual_address_order
    FROM reporting.visit_sequence_deviation
    GROUP BY route_id, import_id
), arrivals AS (
    SELECT route_id, import_id,
           count(*) FILTER (WHERE eligible_delivery) AS eligible_delivery_visit_count,
           count(*) FILTER (WHERE arrival_status = 'late') AS late_delivery_visit_count,
           bool_or(arrival_reversal) AS has_arrival_reversal,
           bool_or(route_timing_span_over_1440) AS route_timing_span_over_1440
    FROM reporting.visit_arrival_window
    WHERE route_id IS NOT NULL
    GROUP BY route_id, import_id
)
SELECT route.route_id, route.import_id, route.country,
       CASE route.country WHEN 0 THEN 'Norway' WHEN 1 THEN 'Denmark' END AS country_name,
       coalesce(sequences.visit_count, 0) AS visit_count,
       CASE
           WHEN sequences.visit_count IS NULL THEN '0'
           WHEN sequences.visit_count <= 5 THEN '1–5'
           WHEN sequences.visit_count <= 10 THEN '6–10'
           WHEN sequences.visit_count <= 20 THEN '11–20'
           ELSE '21+'
       END AS route_size_band,
       coalesce(sequences.valid_sequence, false) AS valid_sequence,
       sequences.planned_visit_order, sequences.actual_visit_order,
       sequences.planned_address_order, sequences.actual_address_order,
       CASE WHEN sequences.valid_sequence THEN sequences.planned_visit_order = sequences.actual_visit_order END
           AS exact_visit_match,
       CASE WHEN sequences.valid_sequence THEN sequences.planned_address_order = sequences.actual_address_order END
           AS exact_address_match,
       coalesce(sequences.moved_visit_count, 0) AS moved_visit_count,
       100 * sequences.moved_visit_count::numeric / nullif(sequences.visit_count, 0) AS moved_visit_pct,
       sequences.total_absolute_position_displacement, sequences.mean_absolute_position_displacement,
       sequences.max_absolute_position_displacement,
       coalesce(arrivals.eligible_delivery_visit_count, 0) AS eligible_delivery_visit_count,
       coalesce(arrivals.late_delivery_visit_count, 0) AS late_delivery_visit_count,
       coalesce(arrivals.eligible_delivery_visit_count > 0, false) AS has_eligible_delivery,
       coalesce(arrivals.late_delivery_visit_count > 0, false) AS has_late_arrival,
       coalesce(arrivals.has_arrival_reversal, false) AS has_arrival_reversal,
       coalesce(arrivals.route_timing_span_over_1440, false) AS route_timing_span_over_1440
FROM core.route AS route
LEFT JOIN sequences USING (route_id, import_id)
LEFT JOIN arrivals USING (route_id, import_id);

CREATE OR REPLACE VIEW reporting.route_sequence_lateness_summary AS
WITH cohorts AS (
    SELECT country, country_name, route_size_band,
           CASE exact_address_match
               WHEN true THEN 'unchanged'
               WHEN false THEN 'changed'
               ELSE 'unverified'
           END AS address_sequence_status,
           visit_count, has_eligible_delivery, has_late_arrival
    FROM reporting.route_sequence_deviation
), totals AS (
    SELECT country, country_name, route_size_band,
           coalesce(address_sequence_status, 'all') AS address_sequence_status,
           count(*) AS route_count,
           coalesce(sum(visit_count), 0) AS visit_count,
           count(*) FILTER (WHERE has_eligible_delivery) AS eligible_route_count,
           count(*) FILTER (WHERE has_late_arrival) AS late_route_count
    FROM cohorts
    GROUP BY GROUPING SETS (
        (), (address_sequence_status),
        (country, country_name), (country, country_name, address_sequence_status),
        (route_size_band), (route_size_band, address_sequence_status),
        (country, country_name, route_size_band),
        (country, country_name, route_size_band, address_sequence_status)
    )
)
SELECT totals.*, late_route_count::numeric / nullif(eligible_route_count, 0) AS late_route_rate
FROM totals;

GRANT SELECT ON reporting.visit_sequence_deviation, reporting.route_sequence_deviation,
                reporting.route_sequence_lateness_summary TO p002_report;
COMMIT;

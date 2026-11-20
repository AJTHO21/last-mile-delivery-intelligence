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

CREATE OR REPLACE VIEW reporting.dashboard_visit AS
SELECT import_id, worksheet_name, source_row_number, route_id, index_p, index_a,
       stop_id, address_id, depot, delivery, arrived_minutes, earliest_minutes, latest_minutes,
       eligible_delivery, eligibility_reason, arrival_status, early_minutes, late_minutes,
       arrival_tie, arrival_reversal, zero_width_window, depot_delivery_overlap,
       route_timing_span_minutes, route_timing_span_over_1440, early_gap_over_1440, late_gap_over_1440
FROM reporting.visit_arrival_window;

CREATE OR REPLACE VIEW reporting.dashboard_route AS
SELECT distance.*, sequence.valid_sequence, sequence.exact_visit_match,
       sequence.moved_visit_count, sequence.moved_visit_pct,
       sequence.max_absolute_position_displacement, sequence.has_arrival_reversal
FROM reporting.route_distance AS distance
JOIN reporting.route_sequence_deviation AS sequence USING (route_id, import_id);

CREATE OR REPLACE VIEW reporting.dashboard_overview AS
WITH visits AS (
    SELECT timing_cohort, count(*) AS source_visit_count,
           count(*) FILTER (WHERE eligible_delivery) AS eligible_delivery_count,
           count(*) FILTER (WHERE arrival_status = 'early') AS early_count,
           count(*) FILTER (WHERE arrival_status = 'in_window') AS in_window_count,
           count(*) FILTER (WHERE arrival_status = 'late') AS late_count,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY late_minutes)
               FILTER (WHERE arrival_status = 'late') AS median_late_minutes,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY late_minutes)
               FILTER (WHERE arrival_status = 'late') AS p90_late_minutes
    FROM reporting.dashboard_visit
    CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route_timing_span_over_1440
        THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
    GROUP BY timing_cohort
), routes AS (
    SELECT timing_cohort, count(*) AS route_count,
           count(*) FILTER (WHERE has_eligible_delivery) AS eligible_route_count,
           count(*) FILTER (WHERE has_late_arrival) AS late_route_count,
           count(*) FILTER (WHERE valid_sequence) AS valid_sequence_route_count,
           count(*) FILTER (WHERE NOT exact_address_match) AS changed_address_route_count,
           count(*) FILTER (WHERE distance_review_flag) AS distance_review_route_count
    FROM reporting.dashboard_route
    CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route_timing_span_over_1440
        THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
    GROUP BY timing_cohort
)
SELECT visits.*, routes.route_count, routes.eligible_route_count, routes.late_route_count,
       routes.valid_sequence_route_count, routes.changed_address_route_count, routes.distance_review_route_count,
       early_count::numeric / nullif(eligible_delivery_count,0) AS early_rate,
       in_window_count::numeric / nullif(eligible_delivery_count,0) AS in_window_rate,
       late_count::numeric / nullif(eligible_delivery_count,0) AS late_delivery_rate,
       late_route_count::numeric / nullif(eligible_route_count,0) AS late_route_rate,
       changed_address_route_count::numeric / nullif(valid_sequence_route_count,0) AS changed_address_route_rate
FROM visits FULL JOIN routes USING (timing_cohort);

GRANT SELECT ON reporting.dashboard_visit, reporting.dashboard_route, reporting.dashboard_overview TO p002_report;
COMMIT;

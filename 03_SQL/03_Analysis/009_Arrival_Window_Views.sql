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

CREATE OR REPLACE VIEW reporting.visit_arrival_window AS
WITH sequenced AS (
    SELECT visit.*,
           lag(arrived_minutes) OVER (PARTITION BY route_id, import_id ORDER BY index_a) AS previous_arrival,
           max(greatest(arrived_minutes, earliest_minutes, latest_minutes)) OVER route_window
             - min(least(arrived_minutes, earliest_minutes, latest_minutes)) OVER route_window AS route_timing_span
    FROM core.visit AS visit
    WINDOW route_window AS (PARTITION BY route_id, import_id)
), assessed AS (
    SELECT source.import_id, source.worksheet_name, source.source_row_number,
           visit.route_id, visit.index_p, visit.index_a, visit.stop_id, visit.address_id,
           route.country, route.driver_id, visit.week_id, visit.day_of_week,
           visit.depot, visit.delivery, visit.arrived_minutes, visit.earliest_minutes, visit.latest_minutes,
           CASE
               WHEN visit.route_id IS NULL THEN 'missing_core_visit'
               WHEN visit.depot THEN 'depot'
               WHEN NOT visit.delivery THEN 'non_delivery'
               WHEN visit.arrived_minutes IS NULL OR visit.earliest_minutes IS NULL
                 OR visit.latest_minutes IS NULL THEN 'missing_timing'
               WHEN NOT (visit.arrived_minutes >= 0 AND visit.arrived_minutes < 'Infinity'::numeric
                 AND visit.earliest_minutes >= 0 AND visit.earliest_minutes < 'Infinity'::numeric
                 AND visit.latest_minutes >= 0 AND visit.latest_minutes < 'Infinity'::numeric
                 AND visit.earliest_minutes <= visit.latest_minutes) THEN 'invalid_timing'
               ELSE 'eligible_delivery'
           END AS eligibility_reason,
           coalesce(visit.arrived_minutes = visit.previous_arrival, false) AS arrival_tie,
           coalesce(visit.arrived_minutes < visit.previous_arrival, false) AS arrival_reversal,
           coalesce(visit.earliest_minutes = visit.latest_minutes, false) AS zero_width_window,
           coalesce(visit.depot AND visit.delivery, false) AS depot_delivery_overlap,
           visit.route_timing_span AS route_timing_span_minutes,
           coalesce(visit.route_timing_span > 1440, false) AS route_timing_span_over_1440
    FROM staging.source_visit AS source
    LEFT JOIN sequenced AS visit USING (import_id, worksheet_name, source_row_number)
    LEFT JOIN core.route AS route ON (route.route_id, route.import_id) = (visit.route_id, visit.import_id)
), classified AS (
    SELECT assessed.*, eligibility_reason = 'eligible_delivery' AS eligible_delivery,
           CASE
               WHEN eligibility_reason <> 'eligible_delivery' THEN NULL
               WHEN arrived_minutes < earliest_minutes THEN 'early'
               WHEN arrived_minutes > latest_minutes THEN 'late'
               ELSE 'in_window'
           END AS arrival_status
    FROM assessed
)
SELECT classified.*,
       CASE WHEN arrival_status = 'early' THEN earliest_minutes - arrived_minutes END AS early_minutes,
       CASE WHEN arrival_status = 'late' THEN arrived_minutes - latest_minutes END AS late_minutes,
       coalesce(arrival_status = 'early' AND earliest_minutes - arrived_minutes > 1440, false)
           AS early_gap_over_1440,
       coalesce(arrival_status = 'late' AND arrived_minutes - latest_minutes > 1440, false)
           AS late_gap_over_1440
FROM classified;

CREATE OR REPLACE VIEW reporting.arrival_window_summary AS
WITH totals AS (
    SELECT count(*) FILTER (WHERE eligible_delivery) AS eligible_delivery_count,
           count(*) FILTER (WHERE arrival_status = 'early') AS early_count,
           count(*) FILTER (WHERE arrival_status = 'in_window') AS in_window_count,
           count(*) FILTER (WHERE arrival_status = 'late') AS late_count,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY late_minutes)
               FILTER (WHERE arrival_status = 'late') AS median_late_minutes,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY late_minutes)
               FILTER (WHERE arrival_status = 'late') AS p90_late_minutes
    FROM reporting.visit_arrival_window
)
SELECT eligible_delivery_count,
       early_count, early_count::numeric / nullif(eligible_delivery_count, 0) AS early_rate,
       in_window_count, in_window_count::numeric / nullif(eligible_delivery_count, 0) AS in_window_rate,
       late_count, late_count::numeric / nullif(eligible_delivery_count, 0) AS late_rate,
       median_late_minutes, p90_late_minutes
FROM totals;

GRANT SELECT ON reporting.visit_arrival_window, reporting.arrival_window_summary TO p002_report;
COMMIT;

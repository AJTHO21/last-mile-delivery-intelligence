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

CREATE OR REPLACE VIEW reporting.route_performance_comparison AS
WITH cohorts AS (
    SELECT cohort.timing_cohort, route.*,
           CASE exact_address_match WHEN true THEN 'unchanged' WHEN false THEN 'changed'
                ELSE 'unverified' END AS address_status
    FROM reporting.route_sequence_deviation AS route
    CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route_timing_span_over_1440
        THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
), counts AS (
    SELECT timing_cohort, country, country_name, route_size_band,
           coalesce(count(*) FILTER (WHERE address_status = 'changed'), 0)::bigint AS changed_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'changed' AND has_eligible_delivery), 0)::bigint AS changed_eligible_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'changed' AND has_late_arrival), 0)::bigint AS changed_late_route_count,
           coalesce(sum(eligible_delivery_visit_count) FILTER (WHERE address_status = 'changed'), 0)::bigint AS changed_eligible_delivery_count,
           coalesce(sum(late_delivery_visit_count) FILTER (WHERE address_status = 'changed'), 0)::bigint AS changed_late_delivery_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unchanged'), 0)::bigint AS unchanged_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unchanged' AND has_eligible_delivery), 0)::bigint AS unchanged_eligible_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unchanged' AND has_late_arrival), 0)::bigint AS unchanged_late_route_count,
           coalesce(sum(eligible_delivery_visit_count) FILTER (WHERE address_status = 'unchanged'), 0)::bigint AS unchanged_eligible_delivery_count,
           coalesce(sum(late_delivery_visit_count) FILTER (WHERE address_status = 'unchanged'), 0)::bigint AS unchanged_late_delivery_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unverified'), 0)::bigint AS unverified_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unverified' AND has_eligible_delivery), 0)::bigint AS unverified_eligible_route_count,
           coalesce(count(*) FILTER (WHERE address_status = 'unverified' AND has_late_arrival), 0)::bigint AS unverified_late_route_count,
           coalesce(sum(eligible_delivery_visit_count) FILTER (WHERE address_status = 'unverified'), 0)::bigint AS unverified_eligible_delivery_count,
           coalesce(sum(late_delivery_visit_count) FILTER (WHERE address_status = 'unverified'), 0)::bigint AS unverified_late_delivery_count
    FROM cohorts
    GROUP BY timing_cohort, GROUPING SETS (
        (), (country, country_name), (route_size_band), (country, country_name, route_size_band)
    )
), rates AS (
    SELECT counts.*,
           changed_late_route_count::numeric / nullif(changed_eligible_route_count, 0) AS changed_route_rate,
           changed_late_delivery_count::numeric / nullif(changed_eligible_delivery_count, 0) AS changed_delivery_rate,
           unchanged_late_route_count::numeric / nullif(unchanged_eligible_route_count, 0) AS unchanged_route_rate,
           unchanged_late_delivery_count::numeric / nullif(unchanged_eligible_delivery_count, 0) AS unchanged_delivery_rate
    FROM counts
)
SELECT rates.*, 100 * (changed_route_rate - unchanged_route_rate) AS route_gap_pp,
       100 * (changed_delivery_rate - unchanged_delivery_rate) AS delivery_gap_pp
FROM rates;

CREATE OR REPLACE VIEW reporting.route_performance_standardization_strata AS
WITH support AS (
    SELECT comparison.*,
           changed_eligible_route_count >= 50 AND unchanged_eligible_route_count >= 50
           AND changed_eligible_delivery_count >= 100 AND unchanged_eligible_delivery_count >= 100
               AS adequate_support,
           changed_eligible_route_count + unchanged_eligible_route_count AS pooled_eligible_routes
    FROM reporting.route_performance_comparison AS comparison
    WHERE country IS NOT NULL AND route_size_band IS NOT NULL
      AND timing_cohort IN ('full', 'span_at_most_1440')
)
SELECT support.*,
       CASE WHEN adequate_support THEN pooled_eligible_routes::numeric /
           nullif(sum(pooled_eligible_routes) FILTER (WHERE adequate_support)
                  OVER (PARTITION BY timing_cohort), 0) END AS common_weight
FROM support;

CREATE OR REPLACE VIEW reporting.route_performance_standardized AS
WITH weighted AS (
    SELECT timing_cohort,
           count(*) AS observed_strata,
           count(*) FILTER (WHERE adequate_support) AS supported_strata,
           sum(pooled_eligible_routes) AS observed_pooled_eligible_routes,
           coalesce(sum(pooled_eligible_routes) FILTER (WHERE adequate_support), 0) AS supported_pooled_eligible_routes,
           sum(common_weight * changed_route_rate) AS changed_route_rate,
           sum(common_weight * unchanged_route_rate) AS unchanged_route_rate,
           sum(common_weight * changed_delivery_rate) AS changed_delivery_rate,
           sum(common_weight * unchanged_delivery_rate) AS unchanged_delivery_rate
    FROM reporting.route_performance_standardization_strata
    GROUP BY timing_cohort
)
SELECT weighted.*, 100 * (changed_route_rate - unchanged_route_rate) AS route_gap_pp,
       100 * (changed_delivery_rate - unchanged_delivery_rate) AS delivery_gap_pp
FROM weighted;

CREATE OR REPLACE VIEW reporting.visit_displacement_lateness AS
WITH banded AS (
    SELECT cohort.timing_cohort, visit.route_id,
           CASE route.exact_address_match WHEN true THEN 'unchanged' WHEN false THEN 'changed'
                ELSE 'unverified' END AS address_status,
           CASE route.exact_visit_match
               WHEN true THEN 'exact_visit_order' WHEN false THEN 'changed_visit_order'
               ELSE 'unverified' END AS visit_order_status,
           CASE absolute_position_displacement WHEN 0 THEN '0' WHEN 1 THEN '1'
             ELSE CASE WHEN absolute_position_displacement <= 3 THEN '2–3'
                       WHEN absolute_position_displacement <= 6 THEN '4–6' ELSE '7+' END
           END AS displacement_band,
           arrival.eligible_delivery, coalesce(arrival.arrival_status = 'late', false) AS late_delivery
    FROM reporting.visit_sequence_deviation AS visit
    JOIN reporting.route_sequence_deviation AS route USING (route_id, import_id)
    LEFT JOIN reporting.visit_arrival_window AS arrival
        USING (import_id, worksheet_name, source_row_number, route_id, index_p)
    CROSS JOIN LATERAL (VALUES ('full'), (CASE WHEN route.route_timing_span_over_1440
        THEN 'removed_over_1440' ELSE 'span_at_most_1440' END)) AS cohort(timing_cohort)
), counts AS (
    SELECT timing_cohort, address_status, visit_order_status, displacement_band,
           count(*) AS visit_count, count(DISTINCT route_id) AS represented_route_count,
           count(*) FILTER (WHERE eligible_delivery) AS eligible_delivery_count,
           count(*) FILTER (WHERE late_delivery) AS late_delivery_count
    FROM banded GROUP BY timing_cohort, address_status, visit_order_status, displacement_band
)
SELECT counts.*, late_delivery_count::numeric / nullif(eligible_delivery_count, 0) AS late_delivery_rate
FROM counts;

GRANT SELECT ON reporting.route_performance_comparison, reporting.route_performance_standardization_strata,
    reporting.route_performance_standardized, reporting.visit_displacement_lateness TO p002_report;
COMMIT;

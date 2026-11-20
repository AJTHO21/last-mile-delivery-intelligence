\set ON_ERROR_STOP on
BEGIN READ ONLY;

DO $$
DECLARE
    totals reporting.arrival_window_summary%ROWTYPE;
    detail_counts bigint[];
    anomaly_counts bigint[];
BEGIN
    WITH detail AS MATERIALIZED (SELECT * FROM reporting.visit_arrival_window)
    SELECT ARRAY[count(*), count(DISTINCT (import_id, worksheet_name, source_row_number)),
                 count(*) FILTER (WHERE eligible_delivery),
                 count(*) FILTER (WHERE arrival_status = 'early'),
                 count(*) FILTER (WHERE arrival_status = 'in_window'),
                 count(*) FILTER (WHERE arrival_status = 'late'),
                 count(*) FILTER (WHERE
                     (eligible_delivery, arrival_status, early_minutes, late_minutes)
                     IS DISTINCT FROM (
                         eligibility_reason = 'eligible_delivery',
                         CASE WHEN eligibility_reason = 'eligible_delivery' THEN
                             CASE WHEN arrived_minutes < earliest_minutes THEN 'early'
                                  WHEN arrived_minutes > latest_minutes THEN 'late'
                                  ELSE 'in_window' END END,
                         CASE WHEN eligible_delivery AND arrived_minutes < earliest_minutes
                              THEN earliest_minutes - arrived_minutes END,
                         CASE WHEN eligible_delivery AND arrived_minutes > latest_minutes
                              THEN arrived_minutes - latest_minutes END
                     )),
                 count(*) FILTER (WHERE eligibility_reason IN ('missing_core_visit', 'missing_timing', 'invalid_timing'))],
           ARRAY[count(*) FILTER (WHERE arrival_tie),
                 count(*) FILTER (WHERE arrival_reversal),
                 count(*) FILTER (WHERE zero_width_window),
                 count(*) FILTER (WHERE depot_delivery_overlap),
                 count(*) FILTER (WHERE early_gap_over_1440),
                 count(*) FILTER (WHERE late_gap_over_1440),
                 count(DISTINCT route_id) FILTER (WHERE route_timing_span_over_1440)]
    INTO detail_counts, anomaly_counts FROM detail;

    IF detail_counts IS DISTINCT FROM ARRAY[249231,249231,213122,24252,165152,23718,0,0]::bigint[]
       OR detail_counts[1] <> (SELECT count(*) FROM staging.source_visit)
       OR detail_counts[1] <> (SELECT count(*) FROM core.visit) THEN
        RAISE EXCEPTION 'Unexpected visit coverage, baseline or classifications: %', detail_counts;
    END IF;

    IF anomaly_counts IS DISTINCT FROM ARRAY[4643,2180,27,4884,155,620,1168]::bigint[] THEN
        RAISE EXCEPTION 'Timing anomaly reconciliation failed: %', anomaly_counts;
    END IF;

    SELECT * INTO STRICT totals FROM reporting.arrival_window_summary;
    IF (totals.eligible_delivery_count, totals.early_count, totals.in_window_count, totals.late_count)
          IS DISTINCT FROM (detail_counts[3], detail_counts[4], detail_counts[5], detail_counts[6])
       OR (totals.early_rate, totals.in_window_rate, totals.late_rate) IS DISTINCT FROM (
           detail_counts[4]::numeric / detail_counts[3],
           detail_counts[5]::numeric / detail_counts[3],
           detail_counts[6]::numeric / detail_counts[3])
       OR round(totals.median_late_minutes::numeric, 2) IS DISTINCT FROM 47.94
       OR round(totals.p90_late_minutes::numeric, 2) IS DISTINCT FROM 206.09 THEN
        RAISE EXCEPTION 'Summary reconciliation failed: %', totals;
    END IF;

    IF NOT has_table_privilege('p002_report', 'reporting.visit_arrival_window', 'SELECT')
       OR NOT has_table_privilege('p002_report', 'reporting.arrival_window_summary', 'SELECT')
       OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE') THEN
        RAISE EXCEPTION 'Unexpected reporting privileges';
    END IF;
END
$$;

SELECT * FROM reporting.arrival_window_summary;
ROLLBACK;

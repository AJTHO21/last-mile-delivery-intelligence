-- Run only in the disposable test database before loading the workbook.
\set ON_ERROR_STOP on
BEGIN;

INSERT INTO staging.source_import (import_id, source_filename, source_doi, source_version, sha256)
OVERRIDING SYSTEM VALUE VALUES (-9009, 'fixture.xlsx', 'fixture', 1, repeat('a', 64));
INSERT INTO staging.source_visit (import_id, worksheet_name, source_row_number)
SELECT -9009, 'Fixture', row_number FROM generate_series(2, 9) AS row_number;
INSERT INTO core.route (route_id, import_id, country, driver_id)
VALUES (99999, -9009, 0, 1);
INSERT INTO core.visit VALUES
    (99999, 0, 0, -9009, 'Fixture', 2, 1, 1, 0, 'Monday',     10, 10, 20, 0, 0, false, true),
    (99999, 1, 1, -9009, 'Fixture', 3, 1, 1, 0, 'Monday',     20, 10, 20, 0, 0, false, true),
    (99999, 2, 2, -9009, 'Fixture', 4, 1, 1, 0, 'Monday',     20, 20, 20, 0, 0, false, true),
    (99999, 3, 3, -9009, 'Fixture', 5, 1, 1, 0, 'Monday',      9, 10, 20, 0, 0, false, true),
    (99999, 4, 4, -9009, 'Fixture', 6, 1, 1, 0, 'Monday',  10000, 10, 20, 0, 0, false, true),
    (99999, 5, 5, -9009, 'Fixture', 7, 1, 1, 0, 'Monday',     21, 10, 20, 0, 0, true,  true),
    (99999, 6, 6, -9009, 'Fixture', 8, 1, 1, 0, 'Monday',      9, 10, 20, 0, 0, false, false);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM (VALUES
            (2, 'eligible_delivery', 'in_window', NULL::numeric, NULL::numeric, false, false, false),
            (3, 'eligible_delivery', 'in_window', NULL, NULL, false, false, false),
            (4, 'eligible_delivery', 'in_window', NULL, NULL, true, false, true),
            (5, 'eligible_delivery', 'early', 1, NULL, false, true, false),
            (6, 'eligible_delivery', 'late', NULL, 9980, false, false, false),
            (7, 'depot', NULL, NULL, NULL, false, true, false),
            (8, 'non_delivery', NULL, NULL, NULL, false, true, false),
            (9, 'missing_core_visit', NULL, NULL, NULL, false, false, false)
        ) AS expected (source_row_number, reason, status, early, late, tie, reversal, zero_width)
        LEFT JOIN reporting.visit_arrival_window AS actual
          ON actual.source_row_number = expected.source_row_number AND actual.import_id = -9009
        WHERE (actual.eligibility_reason, actual.arrival_status, actual.early_minutes, actual.late_minutes,
               actual.arrival_tie, actual.arrival_reversal, actual.zero_width_window)
           IS DISTINCT FROM
              (expected.reason, expected.status, expected.early, expected.late, expected.tie,
               expected.reversal, expected.zero_width)
    ) OR (SELECT count(*) FROM reporting.visit_arrival_window) <> 8
       OR (SELECT (eligible_delivery_count, early_count, in_window_count, late_count,
                   early_rate, in_window_rate, late_rate, median_late_minutes, p90_late_minutes)
           FROM reporting.arrival_window_summary)
           IS DISTINCT FROM ROW(5::bigint, 1::bigint, 3::bigint, 1::bigint,
                                0.2::numeric, 0.6::numeric, 0.2::numeric,
                                9980::double precision, 9980::double precision)
       OR NOT EXISTS (
           SELECT 1 FROM reporting.visit_arrival_window
           WHERE source_row_number = 6 AND arrived_minutes = 10000
             AND late_gap_over_1440 AND route_timing_span_over_1440
       )
    THEN
        RAISE EXCEPTION 'Arrival-window fixture checks failed';
    END IF;
END
$$;
ROLLBACK;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM reporting.arrival_window_summary
        WHERE eligible_delivery_count = 0 AND early_rate IS NULL AND in_window_rate IS NULL
          AND late_rate IS NULL AND median_late_minutes IS NULL AND p90_late_minutes IS NULL
    ) THEN
        RAISE EXCEPTION 'Empty arrival summary should have null rates and percentiles';
    END IF;
END
$$;
SELECT 'Arrival-window fixture checks passed' AS result;

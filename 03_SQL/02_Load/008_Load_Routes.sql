-- Feed the verified staging CSV on psql's standard input.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog, pg_temp;

DO $$
BEGIN
    IF current_database() <> 'p002_last_mile' OR current_user <> 'p002_dev' THEN
        RAISE EXCEPTION 'Run as p002_dev in p002_last_mile';
    END IF;
END
$$;

CREATE TEMP TABLE incoming (LIKE staging.source_visit) ON COMMIT DROP;
ALTER TABLE incoming DROP COLUMN import_id;
ALTER TABLE incoming ADD PRIMARY KEY (worksheet_name, source_row_number);
\copy pg_temp.incoming FROM PSTDIN WITH (FORMAT csv, HEADER MATCH)

-- Count, minimum and maximum together establish contiguous source row lineage.
DO $$
BEGIN
    IF (SELECT (count(*), min(source_row_number), max(source_row_number)) FROM incoming)
          <> ROW(249231::bigint, 2, 249232)
       OR EXISTS (
           SELECT 1 FROM incoming
           WHERE worksheet_name <> 'Sheet1'
              OR NOT coalesce(route_id ~ '^[0-9]+$' AND driver_id ~ '^[0-9]+$'
                  AND stop_id ~ '^[0-9]+$' AND address_id ~ '^[0-9]+$' AND week_id ~ '^[0-9]+$'
                  AND index_p ~ '^[0-9]+$' AND index_a ~ '^[0-9]+$'
                  AND country IN ('0','1') AND depot IN ('0','1') AND delivery IN ('0','1')
                  AND day_of_week IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
                  AND arrived_time IS NOT NULL AND earliest_time IS NOT NULL AND latest_time IS NOT NULL
                  AND distance_p IS NOT NULL AND distance_a IS NOT NULL, false)
       ) THEN
        RAISE EXCEPTION 'Invalid source lineage, required fields or source row count';
    END IF;
END
$$;

-- Serialize publication, including two attempts to load the same workbook.
LOCK TABLE staging.source_import, staging.source_visit, core.route, core.visit
    IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE source_batch ON COMMIT DROP AS
SELECT 'routes_performance.xlsx'::text AS source_filename,
       '10.17632/kkwgfvmtxn.1'::text AS source_doi, 1 AS source_version,
       '8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00'::text AS sha256;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM staging.source_import AS existing CROSS JOIN source_batch AS expected
        WHERE (existing.sha256 = expected.sha256 OR regexp_replace(lower(existing.source_doi), '[.][0-9]+$', '')
              = regexp_replace(expected.source_doi, '[.][0-9]+$', ''))
          AND (existing.source_filename, existing.source_doi, existing.source_version, existing.sha256)
           IS DISTINCT FROM (expected.source_filename, expected.source_doi, expected.source_version, expected.sha256)
    ) THEN
        RAISE EXCEPTION 'Conflicting source hash or version metadata';
    END IF;
END
$$;

CREATE TEMP TABLE new_import ON COMMIT DROP AS
WITH inserted AS (
    INSERT INTO staging.source_import (source_filename, source_doi, source_version, sha256)
    SELECT expected.* FROM source_batch AS expected
    WHERE NOT EXISTS (SELECT 1 FROM staging.source_import WHERE sha256 = expected.sha256)
    RETURNING import_id
)
SELECT import_id FROM inserted;

CREATE TEMP TABLE expected_stage ON COMMIT DROP AS
SELECT batch.import_id, incoming.*
FROM incoming
JOIN source_batch AS expected ON true
JOIN staging.source_import AS batch USING (sha256);

-- Explicit decimal casts preserve the source XML's exact numeric values.
CREATE TEMP TABLE expected_visit ON COMMIT DROP AS
SELECT route_id::integer, index_p::integer, index_a::integer,
       import_id, worksheet_name, source_row_number, stop_id::integer, address_id::integer,
       week_id::integer, day_of_week,
       arrived_time::numeric AS arrived_minutes, earliest_time::numeric AS earliest_minutes,
       latest_time::numeric AS latest_minutes, distance_p::numeric AS distance_p_km,
       distance_a::numeric AS distance_a_km, depot = '1' AS depot, delivery = '1' AS delivery
FROM expected_stage;

CREATE TEMP TABLE expected_route ON COMMIT DROP AS
SELECT DISTINCT route_id::integer, import_id, country::smallint, driver_id::integer
FROM expected_stage;

DO $$
BEGIN
    IF (SELECT count(*) FROM expected_route) <> 19647
       OR (SELECT count(DISTINCT route_id) FROM expected_route) <> 19647
       OR EXISTS (
           SELECT 1 FROM expected_visit GROUP BY route_id
           HAVING min(index_p) <> 0 OR min(index_a) <> 0
               OR max(index_p) <> count(*) - 1 OR max(index_a) <> count(*) - 1
               OR count(DISTINCT index_p) <> count(*) OR count(DISTINCT index_a) <> count(*)
       ) THEN
        RAISE EXCEPTION 'Route assignment, route count, or permutation mismatch';
    END IF;

    IF EXISTS (
        SELECT 1 FROM core.route AS existing JOIN expected_route AS expected USING (route_id)
        WHERE existing.import_id <> expected.import_id
    ) THEN
        RAISE EXCEPTION 'At least one route ID belongs to another import';
    END IF;
END
$$;

INSERT INTO staging.source_visit SELECT * FROM expected_stage
WHERE EXISTS (SELECT 1 FROM new_import);
INSERT INTO core.route SELECT * FROM expected_route
WHERE EXISTS (SELECT 1 FROM new_import);
INSERT INTO core.visit SELECT * FROM expected_visit
WHERE EXISTS (SELECT 1 FROM new_import);

-- Repeat loads are exact no-ops. Compare all rows and columns, including
-- source text and lineage. Counts also catch unexpected surplus rows.
DO $$
DECLARE
    batch_id bigint := (SELECT import_id FROM staging.source_import JOIN source_batch USING (sha256));
BEGIN
    IF (SELECT count(*) FROM staging.source_visit WHERE import_id = batch_id) <> 249231
       OR (SELECT count(*) FROM core.route WHERE import_id = batch_id) <> 19647
       OR (SELECT count(*) FROM core.visit WHERE import_id = batch_id) <> 249231
       OR EXISTS (SELECT * FROM expected_stage EXCEPT SELECT * FROM staging.source_visit WHERE import_id = batch_id)
       OR EXISTS (SELECT * FROM expected_route EXCEPT SELECT * FROM core.route WHERE import_id = batch_id)
       OR EXISTS (SELECT * FROM expected_visit EXCEPT SELECT * FROM core.visit WHERE import_id = batch_id)
       OR (
           SELECT (count(*), count(*) FILTER (WHERE NOT visit.depot AND visit.delivery),
                   count(*) FILTER (WHERE NOT visit.depot AND visit.delivery
                                     AND visit.arrived_minutes > visit.latest_minutes))
           FROM core.visit AS visit
           JOIN core.route AS route USING (route_id, import_id)
           JOIN staging.source_visit AS source USING (import_id, worksheet_name, source_row_number)
           WHERE visit.import_id = batch_id
       ) <> ROW(249231::bigint, 213122::bigint, 23718::bigint)
    THEN
        RAISE EXCEPTION 'Stored rows or operational reconciliation differ from verified input';
    END IF;
END
$$;

COMMIT;
SELECT 'P002 load reconciled' AS result;

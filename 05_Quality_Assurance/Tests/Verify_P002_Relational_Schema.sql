\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
    fixture_import constant bigint := -7007;
    other_import constant bigint := -7008;
    fixture_route constant integer := 2147483647;
    rejected_case record;
    actual_constraint text;
BEGIN
    IF current_database() <> 'p002_last_mile' OR current_user <> 'p002_dev' THEN
        RAISE EXCEPTION 'Run this test as p002_dev in p002_last_mile';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_class AS relation
        JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
        WHERE (namespace.nspname, relation.relname) IN (
            ('staging', 'source_import'), ('staging', 'source_visit'),
            ('core', 'route'), ('core', 'visit')
        ) AND (relation.relkind <> 'r' OR relation.relowner <> 'p002_dev'::regrole)
    ) OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE')
       OR has_table_privilege('p002_report', 'core.visit', 'SELECT, INSERT, UPDATE, DELETE')
    THEN
        RAISE EXCEPTION 'Unexpected table ownership, type, or reporting access';
    END IF;

    -- Explicit fixture IDs avoid advancing the production identity sequence.
    INSERT INTO staging.source_import (import_id, source_filename, source_doi, source_version, sha256)
    OVERRIDING SYSTEM VALUE
    VALUES (fixture_import, 'fixture.xlsx', 'fixture', 1, repeat('a', 64)),
           (other_import, 'other-fixture.xlsx', 'fixture', 1, repeat('b', 64));
    INSERT INTO staging.source_visit (import_id, worksheet_name, source_row_number)
    SELECT fixture_import, 'Sheet1', source_row_number
    FROM generate_series(2, 7) AS source_row_number;
    INSERT INTO staging.source_visit (import_id, worksheet_name, source_row_number)
    VALUES (other_import, 'Sheet1', 2);
    INSERT INTO core.route (route_id, import_id, country, driver_id)
    VALUES (fixture_route, fixture_import, 1, 0);

    -- Repeated stop/depot and address codes, swapped positions, and reversed arrivals.
    INSERT INTO core.visit VALUES
        (fixture_route, 0, 0, fixture_import, 'Sheet1', 2, 7, 9, 0, 'Monday', 4.125, 0, 5, 0, 0, true, false),
        (fixture_route, 1, 2, fixture_import, 'Sheet1', 3, 7, 9, 0, 'Monday', 2.375, 0, 5, 0, 0, true, true),
        (fixture_route, 2, 1, fixture_import, 'Sheet1', 4, 8, 9, 0, 'Monday', 3.5, 1, 1, 0, 0.0566, false, true);

    IF (
        SELECT count(*) FROM core.visit AS visit
        JOIN core.route AS route USING (route_id, import_id)
        JOIN staging.source_visit AS source USING (import_id, worksheet_name, source_row_number)
        JOIN staging.source_import AS batch USING (import_id)
        WHERE visit.route_id = fixture_route
    ) <> 3 THEN
        RAISE EXCEPTION 'Expected exactly three lineage-preserving joined visits';
    END IF;

    FOR rejected_case IN
        SELECT * FROM (VALUES
            ('visit_pk',                    0, 3, fixture_import, 5, fixture_route,     0, 5, 0::numeric),
            ('visit_actual_position_key',   3, 0, fixture_import, 5, fixture_route,     0, 5, 0),
            ('visit_source_row_key',        3, 3, fixture_import, 2, fixture_route,     0, 5, 0),
            ('visit_source_row_fk',         3, 3, fixture_import, 8, fixture_route,     0, 5, 0),
            ('visit_route_fk',              3, 3, other_import,   2, fixture_route,     0, 5, 0),
            ('visit_route_fk',              3, 3, fixture_import, 5, fixture_route - 1, 0, 5, 0),
            ('visit_index_p_check',        -1, 3, fixture_import, 5, fixture_route,     0, 5, 0),
            ('visit_window_order',          3, 3, fixture_import, 5, fixture_route,     6, 5, 0),
            ('visit_distance_p_km_check',   3, 3, fixture_import, 5, fixture_route,     0, 5, -1),
            ('visit_distance_p_km_check',   3, 3, fixture_import, 5, fixture_route,     0, 5, 'NaN'::numeric)
        ) AS cases(constraint_name, index_p, index_a, import_id, source_row_number, route_id, earliest, latest, distance)
    LOOP
        BEGIN
            INSERT INTO core.visit VALUES (
                rejected_case.route_id, rejected_case.index_p, rejected_case.index_a,
                rejected_case.import_id, 'Sheet1', rejected_case.source_row_number,
                7, 9, 0, 'Monday', 2.5, rejected_case.earliest, rejected_case.latest,
                rejected_case.distance, 0, false, true
            );
            RAISE EXCEPTION 'Expected rejection by %', rejected_case.constraint_name;
        EXCEPTION WHEN integrity_constraint_violation THEN
            GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
            IF actual_constraint <> rejected_case.constraint_name THEN
                RAISE EXCEPTION 'Expected %, got %', rejected_case.constraint_name, actual_constraint;
            END IF;
        END;
    END LOOP;
END
$$;

SELECT 'P002 relational schema checks passed' AS result;
ROLLBACK;

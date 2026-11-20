\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
    IF current_database() <> 'p002_last_mile' OR current_user <> 'p002_dev' THEN
        RAISE EXCEPTION 'Run this migration as p002_dev in p002_last_mile';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS staging.source_import (
    import_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_filename text NOT NULL CHECK (btrim(source_filename) <> ''),
    source_doi text NOT NULL CHECK (btrim(source_doi) <> ''),
    source_version integer NOT NULL CHECK (source_version > 0),
    sha256 text NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    imported_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Keep the source cell text for validation and reject tracing during the later load.
CREATE TABLE IF NOT EXISTS staging.source_visit (
    import_id bigint NOT NULL REFERENCES staging.source_import (import_id),
    worksheet_name text NOT NULL CHECK (btrim(worksheet_name) <> ''),
    source_row_number integer NOT NULL CHECK (source_row_number >= 2),
    route_id text,
    driver_id text,
    stop_id text,
    address_id text,
    week_id text,
    country text,
    day_of_week text,
    index_p text,
    index_a text,
    arrived_time text,
    earliest_time text,
    latest_time text,
    distance_p text,
    distance_a text,
    depot text,
    delivery text,
    PRIMARY KEY (import_id, worksheet_name, source_row_number)
);

CREATE TABLE IF NOT EXISTS core.route (
    route_id integer PRIMARY KEY CHECK (route_id >= 0),
    import_id bigint NOT NULL REFERENCES staging.source_import (import_id),
    country smallint NOT NULL CHECK (country IN (0, 1)),
    driver_id integer NOT NULL CHECK (driver_id >= 0),
    UNIQUE (route_id, import_id)
);

CREATE TABLE IF NOT EXISTS core.visit (
    route_id integer NOT NULL,
    index_p integer NOT NULL CHECK (index_p >= 0),
    index_a integer NOT NULL CHECK (index_a >= 0),
    import_id bigint NOT NULL,
    worksheet_name text NOT NULL,
    source_row_number integer NOT NULL,
    stop_id integer NOT NULL CHECK (stop_id >= 0),
    address_id integer NOT NULL CHECK (address_id >= 0),
    week_id integer NOT NULL CHECK (week_id >= 0),
    day_of_week text NOT NULL CHECK (day_of_week IN (
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    )),
    arrived_minutes numeric NOT NULL CHECK (arrived_minutes >= 0 AND arrived_minutes < 'Infinity'::numeric),
    earliest_minutes numeric NOT NULL CHECK (earliest_minutes >= 0 AND earliest_minutes < 'Infinity'::numeric),
    latest_minutes numeric NOT NULL CHECK (latest_minutes >= 0 AND latest_minutes < 'Infinity'::numeric),
    distance_p_km numeric NOT NULL CHECK (distance_p_km >= 0 AND distance_p_km < 'Infinity'::numeric),
    distance_a_km numeric NOT NULL CHECK (distance_a_km >= 0 AND distance_a_km < 'Infinity'::numeric),
    depot boolean NOT NULL,
    delivery boolean NOT NULL,
    CONSTRAINT visit_pk PRIMARY KEY (route_id, index_p),
    CONSTRAINT visit_actual_position_key UNIQUE (route_id, index_a),
    CONSTRAINT visit_source_row_key UNIQUE (import_id, worksheet_name, source_row_number),
    CONSTRAINT visit_route_fk FOREIGN KEY (route_id, import_id)
        REFERENCES core.route (route_id, import_id),
    CONSTRAINT visit_source_row_fk FOREIGN KEY (import_id, worksheet_name, source_row_number)
        REFERENCES staging.source_visit (import_id, worksheet_name, source_row_number),
    CONSTRAINT visit_window_order CHECK (earliest_minutes <= latest_minutes),
    CONSTRAINT visit_first_legs_zero CHECK (
        (index_p <> 0 OR distance_p_km = 0) AND (index_a <> 0 OR distance_a_km = 0)
    )
);

CREATE INDEX IF NOT EXISTS route_import_id_idx ON core.route (import_id);

COMMIT;

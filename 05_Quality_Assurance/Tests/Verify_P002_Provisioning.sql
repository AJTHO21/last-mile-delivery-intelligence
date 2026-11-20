-- Run with psql as the local administrator against p002_last_mile.
\set ON_ERROR_STOP on

DO $$
BEGIN
    IF current_database() <> 'p002_last_mile' OR NOT EXISTS (
        SELECT 1 FROM pg_database
        WHERE datname = current_database() AND datdba = 'p002_owner'::regrole
    ) THEN
        RAISE EXCEPTION 'Wrong database or owner';
    END IF;

    IF (
        SELECT count(*) FROM pg_roles
        WHERE rolname IN ('p002_owner', 'p002_dev', 'p002_report')
          AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
          AND rolcanlogin = (rolname <> 'p002_owner')
    ) <> 3 OR EXISTS (
        SELECT 1 FROM pg_auth_members
        WHERE member IN ('p002_owner'::regrole, 'p002_dev'::regrole, 'p002_report'::regrole)
           OR roleid IN ('p002_owner'::regrole, 'p002_dev'::regrole, 'p002_report'::regrole)
    ) THEN
        RAISE EXCEPTION 'Unexpected role attributes or memberships';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_database AS db
        CROSS JOIN LATERAL aclexplode(coalesce(db.datacl, acldefault('d', db.datdba))) AS acl
        WHERE db.datname = current_database() AND acl.grantee = 0
    ) OR NOT has_database_privilege('p002_dev', current_database(), 'CONNECT')
       OR NOT has_database_privilege('p002_dev', current_database(), 'TEMPORARY')
       OR has_database_privilege('p002_dev', current_database(), 'CREATE')
       OR NOT has_database_privilege('p002_report', current_database(), 'CONNECT')
       OR has_database_privilege('p002_report', current_database(), 'CREATE, TEMPORARY')
    THEN
        RAISE EXCEPTION 'Unexpected P002 database privileges';
    END IF;

    IF (
        SELECT count(*) FROM pg_namespace
        WHERE nspname IN ('staging', 'core', 'reporting')
          AND nspowner = 'p002_dev'::regrole
    ) <> 3 OR NOT has_schema_privilege('p002_report', 'reporting', 'USAGE')
       OR has_schema_privilege('p002_report', 'reporting', 'CREATE')
       OR has_schema_privilege('p002_report', 'staging', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'core', 'USAGE, CREATE')
       OR has_schema_privilege('p002_report', 'public', 'USAGE, CREATE')
    THEN
        RAISE EXCEPTION 'Unexpected P002 schema privileges';
    END IF;
END
$$;

SELECT current_database() AS database_name, pg_get_userbyid(datdba) AS owner
FROM pg_database WHERE datname = current_database();
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname IN ('p002_owner', 'p002_dev', 'p002_report') ORDER BY rolname;

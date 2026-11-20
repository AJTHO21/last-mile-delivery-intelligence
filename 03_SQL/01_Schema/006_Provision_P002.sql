-- Run with psql as the local PostgreSQL administrator against the postgres database.
\set ON_ERROR_STOP on

BEGIN;
DO $$
BEGIN
    IF current_database() <> 'postgres' OR NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = current_user AND rolsuper
    ) THEN
        RAISE EXCEPTION 'Run as the local superuser against the postgres maintenance database';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_database AS db
        JOIN pg_roles AS owner ON owner.oid = db.datdba
        WHERE db.datname = 'p002_last_mile' AND owner.rolname <> 'p002_owner'
    ) THEN
        RAISE EXCEPTION 'Existing p002_last_mile has a different owner';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname IN ('p002_owner', 'p002_dev', 'p002_report')
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication
               OR rolbypassrls OR rolcanlogin <> (rolname <> 'p002_owner'))
    ) OR EXISTS (
        SELECT 1
        FROM pg_auth_members AS membership
        JOIN pg_roles AS project_role ON project_role.oid IN (membership.member, membership.roleid)
        WHERE project_role.rolname IN ('p002_owner', 'p002_dev', 'p002_report')
    ) THEN
        RAISE EXCEPTION 'Existing P002 roles have unexpected attributes or memberships';
    END IF;
END
$$;

SELECT 'CREATE ROLE p002_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'p002_owner')
\gexec
SELECT 'CREATE ROLE p002_dev LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'p002_dev')
\gexec
SELECT 'CREATE ROLE p002_report LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'p002_report')
\gexec
COMMIT;

-- PostgreSQL requires CREATE DATABASE to run outside a transaction.
SELECT 'CREATE DATABASE p002_last_mile OWNER p002_owner ALLOW_CONNECTIONS false'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'p002_last_mile')
\gexec

BEGIN;
REVOKE ALL ON DATABASE p002_last_mile FROM PUBLIC, p002_dev, p002_report;
GRANT CONNECT, TEMPORARY ON DATABASE p002_last_mile TO p002_dev;
GRANT CONNECT ON DATABASE p002_last_mile TO p002_report;
ALTER DATABASE p002_last_mile ALLOW_CONNECTIONS true;
COMMIT;

\connect p002_last_mile
BEGIN;
CREATE SCHEMA IF NOT EXISTS staging AUTHORIZATION p002_dev;
CREATE SCHEMA IF NOT EXISTS core AUTHORIZATION p002_dev;
CREATE SCHEMA IF NOT EXISTS reporting AUTHORIZATION p002_dev;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname IN ('staging', 'core', 'reporting')
          AND nspowner <> 'p002_dev'::regrole
    ) THEN
        RAISE EXCEPTION 'Existing P002 schema has a different owner';
    END IF;
END
$$;

REVOKE ALL ON SCHEMA public FROM PUBLIC, p002_dev, p002_report;
REVOKE ALL ON SCHEMA staging, core, reporting FROM PUBLIC, p002_report;
GRANT USAGE ON SCHEMA reporting TO p002_report;
COMMIT;

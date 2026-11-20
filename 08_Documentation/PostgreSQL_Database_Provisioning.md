# P002 PostgreSQL database provisioning

**Phase 2, Task 006 · 2026-11-19**

Task 007 records successful Task 006 provisioning of `p002_last_mile` and verified connections as `p002_dev` and `p002_report` in the normal Ubuntu WSL terminal, as indicated in the task handoff. The restricted session could not independently repeat those login checks.

| Name | Intended access |
|---|---|
| `p002_last_mile` | Dedicated database. Revoke default public database and public schema access. |
| `p002_owner` | Non-login database owner with no role memberships or cluster administration flags. |
| `p002_dev` | Login with P002 connection and temporary-table rights. Owns `staging`, `core`, and `reporting` schemas for later development. |
| `p002_report` | Login with P002 connection and usage of the `reporting` schema. Grant SELECT explicitly on approved views when they exist. |

The [provisioning script](../03_SQL/01_Schema/006_Provision_P002.sql) creates project roles, the database, and empty schemas. It checks existing role attributes and memberships, database ownership, and schema ownership. Review any name conflict before running again. Re-running a successful setup preserves role passwords and reapplies the same P002 grants. Run one administrator invocation at a time. Database creation runs outside a transaction, so rerun after resolving any interruption. No access rules on other databases are changed. PostgreSQL roles are cluster-wide and may still connect to other databases that grant `CONNECT` to `PUBLIC`, subject to local authentication.

## Provisioning procedure for a fresh environment

Confirm `18/main` is online on port 5432. Use the Unix socket and the `postgres` OS account for peer-authenticated administration. Shell input redirection lets the administrator read scripts from the project without changing project filesystem permissions.

```bash
# Run from the repository root.
sudo pg_lsclusters
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -d postgres \
  -c 'SELECT current_user, version();'
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -d postgres \
  < 03_SQL/01_Schema/006_Provision_P002.sql
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -d p002_last_mile \
  < 05_Quality_Assurance/Tests/Verify_P002_Provisioning.sql
```

Stop on any error. The [verification script](../05_Quality_Assurance/Tests/Verify_P002_Provisioning.sql) checks database ownership, removal of public database grants, cluster flags and role memberships, and effective database and schema access.

Use the Unix socket for project logins if an existing peer mapping allows it. With the standard Ubuntu peer setup, the current Linux user and the two project login names differ. In that case, use the existing local TCP authentication rules with interactive password prompts. Set each login's password once from this admin session, then exit with `\q`. The session-level setting generates SCRAM verifiers and leaves the global configuration alone.

```bash
sudo -u postgres psql -X -h /var/run/postgresql -p 5432 -d postgres
```

```text
SET password_encryption = 'scram-sha-256';
\password p002_dev
\password p002_report
\q
```

Test both project logins. Each result should show `p002_last_mile`, the expected login, and `127.0.0.1` as server address. The reporting access check should return true for usage of `reporting` and false for each of the other three permissions.

```bash
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -c 'SELECT current_database(), current_user, inet_server_addr();'
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_report -d p002_last_mile \
  -c 'SELECT current_database(), current_user, inet_server_addr();' \
  -c "SELECT has_schema_privilege('reporting', 'USAGE') AS reporting_usage, has_schema_privilege('reporting', 'CREATE') AS reporting_create, has_schema_privilege('staging', 'USAGE') AS staging_usage, has_schema_privilege('core', 'USAGE') AS core_usage;"
```

## Verification status

The Task 007 handoff confirms development and reporting connections. Detailed catalog verification output was not supplied. This session did not re-run provisioning. See the [relational schema runbook](PostgreSQL_Relational_Schema.md) for the next migration and tests.

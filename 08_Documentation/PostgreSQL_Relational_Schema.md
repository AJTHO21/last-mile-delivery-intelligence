# P002 initial relational schema

**Phase 2, Task 007 · PostgreSQL 18.6**

## Tables and relationships

| Table | Grain and constraints |
|---|---|
| `staging.source_import` | One import per unique SHA-256. Identity key, source filename, DOI, version, and import time. |
| `staging.source_visit` | One source row per import and worksheet. Key is `(import_id, worksheet_name, source_row_number)`. Source cells are nullable text so later load validation can retain malformed values with lineage. |
| `core.route` | One route per original `route_id`, with import, country and driver identifiers. The additional unique key `(route_id, import_id)` supports the visit foreign key. |
| `core.visit` | One visit per `(route_id, index_p)`, with unique `(route_id, index_a)`. A unique source-row reference links each visit to staging. A composite foreign key requires the linked route to belong to the same import. |

Join visits to routes by `route_id` or by the full route foreign key. Join to staging by the full source-row key. Stop and address codes can repeat, including at depots. Relative times and Haversine leg distances are stored as unrestricted-precision numeric values with nonnegative, finite-value checks. Typed rows require ordered window bounds and zero distance at each order's first position. Zero-width windows, arrival reversals and overlapping depot/delivery flags are preserved.

The initial core represents one accepted source snapshot. A repeated import of the same bytes has one staging import identity. Publishing a new snapshot that reuses route IDs will require a later load policy. Contiguous positions and one consistent country and driver per source route are cross-row validations for the later load.

## Execution order in Ubuntu WSL

Task 006 provisioning is the prerequisite. Run the [version 007 migration](../03_SQL/01_Schema/007_Initial_Relational_Schema.sql) as `p002_dev`, then the [schema verification](../05_Quality_Assurance/Tests/Verify_P002_Relational_Schema.sql) under the same role. Both scripts stop on errors. The migration is transactional and can be rerun against the schema it created. The test checks behavior after migration. Unexpected schema drift requires a separate migration.

```bash
# Run from the repository root.
psql -X -W -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/01_Schema/007_Initial_Relational_Schema.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Relational_Schema.sql
```

The final test result should be `P002 relational schema checks passed`. The tests check table ownership, reporting access, duplicate positions, missing or mismatched parents and lineage, invalid numeric values, and preservation of repeated stop and depot visits in joins. Synthetic rows are rolled back.

## Verification status

The migration ran twice on a disposable PostgreSQL 18.6 instance in standalone mode. Its SQL assertions passed and zero visit rows remained after rollback. The test harness used temporary roles and schemas and removed the temporary instance after the run. The live cluster migration and verification are pending. This session's Unix socket connection returned `Operation not permitted`, loopback access failed, and sudo elevation is unavailable. The WSL command above uses the existing login and an interactive password prompt. No workbook rows, production dashboard views, or credentials are included.

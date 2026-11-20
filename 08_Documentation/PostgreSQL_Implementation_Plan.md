# Proposed PostgreSQL implementation

PostgreSQL will hold the analysis model. Python will read the audited XLSX and prepare load files. The dashboard will consume analysis views or reviewed aggregate extracts. The [environment assessment](PostgreSQL_Environment_Assessment.md) identifies the native ARM64 package candidates and local access plan. Query performance remains to be verified during implementation.

| Layer | Proposed responsibility |
|---|---|
| Staging | Read the workbook without saving changes and validate the source checksum and headers. Bulk load with client-side CSV copy. Retain file hash, worksheet, and source row number. |
| Core routes | One row per `route_id` with consistent country and driver. Interpret driver identity through `(country, driver_id)`. |
| Core visits | One row per `(route_id, index_p)`, foreign key to route and unique `(route_id, index_a)`. Preserve source stop and address codes, weekday, week, boolean flags, relative numeric minutes, and numeric geodesic km. |
| Reporting | Visit-level eligibility and exception flags, route-level order and distance comparisons, and summaries grouped by country and route-size band. |

Validate integer indices and require each planned and actual ordering to contain exactly the zero-based positions for that route. Validate types, domains, time-window ordering, and first-leg values. Record any rejected rows with source lineage and fail publication of a load when required reconciliation checks fail. Keep valid but unusual measurements with explicit QA flags.

Load and validate a version as a unit before exposing reporting results. Use a transaction to publish validated core tables together and identify imports by source hash so reruns preserve counts and keys. Build predecessor comparisons with window functions ordered separately by each source index. Start with primary and unique indexes on the route and visit keys and evaluate additional indexes against observed queries.

Reconcile the baseline 249,231 visits and 19,647 routes and cross-check SQL metrics against the [Phase 0 Python audit](../05_Quality_Assurance/Phase_0_Evidence/audit_workbook.py). Check examples with depot revisits, duplicated addresses, identical boundary times, timing reversals, and zero planned distance. Read reporting views with a read-only database role and keep connection credentials outside the repository.

The target database is `p002_last_mile`. See the [provisioning runbook](PostgreSQL_Database_Provisioning.md) for the database owner, development and reporting roles, and verification commands.

The [initial relational schema](PostgreSQL_Relational_Schema.md) implements staging lineage and the route and visit grains.

The [Task 008 ingestion runbook](PostgreSQL_Ingestion_Runbook.md) documents the verified workbook extractor, transactional loader, reconciliation tests, and live execution command.

The [Task 009 arrival-window KPI runbook](PostgreSQL_Arrival_Window_KPIs.md) defines visit eligibility, reporting views, and validation.

The [Task 010 route sequence runbook](PostgreSQL_Route_Sequence_Analytics.md) documents ordered visit and address comparisons, route-level lateness cohorts, and deployment.

The [Task 011 route performance runbook](PostgreSQL_Route_Performance_Comparisons.md) documents crude and standardized comparisons, timing sensitivity, displacement cohorts, and deployment.

The [Task 012 distance analytics runbook](PostgreSQL_Route_Distance_Analytics.md) defines geodesic distance, anomaly flags, timing sensitivity, and deployment.

The [Task 013 technical QA report](../05_Quality_Assurance/013_Consolidated_Technical_QA.md) indexes the final analytical definitions, consolidated read-only checks, and verification evidence. The [client findings](../07_Reports_and_Delivery/013_Analytical_Findings.md) synthesize the verified results.

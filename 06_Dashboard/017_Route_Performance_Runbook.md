# Route Performance & Exceptions

**P002 · Task 017 · Page 2**

The [dashboard entry point](dashboard.py) opens Executive Overview and Route Performance & Exceptions. They share the timing selection in the navigation sidebar. Page 1 and the Task 015 smoke app can still launch independently. [Approved design](014_Dashboard_Architecture.md) · [Wireframes](014_Dashboard_Wireframes.md) · [Data contract](014_Dashboard_Data_Contract.md)

## Page scope and queries

The [Page 2 app](route_performance.py) uses the [read-only reporting reader](route_performance_data.py). Each connection fixes PostgreSQL to loopback and `p002_report`, uses the existing private passfile, and binds all filter and pagination values. The page caches successful reads for up to two minutes.

| Section | Approved view and behavior |
|---|---|
| Late routes by address order | `reporting.route_performance_comparison`, country × size rows only. Timing, country, and size filter the rows. Both address groups remain visible with total routes and late / eligible routes. |
| Displacement and late deliveries | `reporting.visit_displacement_lateness`. Timing and this panel's address and visit order selectors apply. Country and size are pooled. Each band shows eligible and late deliveries, all visits, and distinct represented routes. A route may contribute to several bands. |
| Route exceptions | `reporting.dashboard_route`. Uses timing, country and size plus optional exact numeric route ID, address status and exception category. All routes are available by default and ordered by late-delivery count, then route and import IDs. A page displays 25 rows. The query requests up to 26 to detect a next page. Changing filters or search returns to page 1. |
| Selected route | `reporting.dashboard_visit`, matched by route and import ID. Both indices, stop and address identifiers, outcomes, eligibility reasons, flags, window offsets, durations and source lineage are shown. Rows sort by recorded actual position. The query returns at most 50 visits per page and additional pages preserve repeat and ineligible visits. |

Route rows and visit detail are fetched separately. The route table's late-delivery rate uses that route's eligible visits. A late route has at least one eligible late arrival. Timing review on the route list covers an arrival reversal or a span above 1,440 minutes. The drill shows the additional visit-level timing flags. A retained cohort excludes long-span routes only and leaves shorter-span timing flags visible.

The comparisons are observational. A route with more delivery visits has more chances to register a late arrival. Early arrival can reflect waiting. The workbook uses relative minutes and straight-line geodesic distances. The page shows no individual driver comparisons.

## Launch in normal Ubuntu WSL

Use the existing Task 015 environment and private passfile at `~/.config/p002/pgpass`. Stop any older P002 Streamlit process already using port 8501 with Ctrl+C. [Dependency and passfile setup](015_Streamlit_Smoke_Runbook.md)

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run dashboard.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --theme.base light --theme.primaryColor '#58758C' --theme.textColor '#182431'
```

Open `http://127.0.0.1:8501` in the Windows browser and select **Route Performance & Exceptions**. Select a country and size band to verify that the late-route comparison and route list update, while the displacement panel remains pooled by country and size. Use **Next**, then search for route **7545** with Full timing and All country, size, address and exception filters. Confirm the list returns to page 1 and selecting the route displays visits in recorded actual order with source row and flags.

## Automated checks

```bash
# Run from the repository root.
.venv/bin/python -B 05_Quality_Assurance/Tests/test_route_performance.py -v
.venv/bin/python -B 05_Quality_Assurance/Tests/test_executive_overview.py -v
.venv/bin/python -B 05_Quality_Assurance/Tests/test_dashboard_smoke.py -v
```

Run the Page 2 test against the actual local reporting login by using:

```bash
env -u PGPASSWORD P002_ROUTE_LIVE=1 \
  .venv/bin/python -B 05_Quality_Assurance/Tests/test_route_performance.py -v
```

### Observed QA

Eight Page 2 tests passed, covering bounded and parameterized queries, reporting-role enforcement, cohort and panel scope, page resets, route drill-through, redacted connection errors, and timing persistence across navigation. Six Page 1 checks and three smoke-app checks passed. Live-login checks were skipped.

All four Page 2 query shapes ran as prepared statements under `p002_report` against the full verified extract in disposable PostgreSQL 18.6. They returned the scoped comparisons, displacement bands, two bounded route pages, one result for exact route ID 7545, and visits in recorded actual order. The sandbox denied the live PostgreSQL socket. Windows browser layout and host authentication remain to be confirmed from normal WSL.

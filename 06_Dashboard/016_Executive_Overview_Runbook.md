# Executive Overview

**P002 · Task 016 · Page 1**

The [Page 1 app](executive_overview.py) follows the approved [wireframe](014_Dashboard_Wireframes.md) and [data contract](014_Dashboard_Data_Contract.md). Use the same private credentials and virtual environment as the independently runnable [Task 015 smoke app](015_Streamlit_Smoke_Runbook.md).

## Data and behavior

The [data reader](executive_overview_data.py) connects to local PostgreSQL exclusively as `p002_report`. It reads three approved views in one read-only repeatable-read transaction.

| App output | PostgreSQL source and scope |
|---|---|
| Four KPI cards and arrival distribution | `reporting.dashboard_overview`, selected timing cohort. The late-delivery denominator is eligible deliveries, the late-route denominator is routes with eligible deliveries, and the address-order denominator is valid sequences. Median and P90 use late eligible deliveries. |
| Crude changed and unchanged rates | `reporting.route_performance_comparison`, selected timing cohort and the pooled country and size row. Count the eligible routes or deliveries separately for each address group. |
| Standardized changed and unchanged rates | `reporting.route_performance_standardized`, selected timing cohort only. Show supported strata and pooled eligible-route coverage. Delivery rates use within-stratum visit rates and common route weights. |
| Timing audit readout | `reporting.dashboard_overview`, removed cohort only. It shows how many routes, eligible deliveries and late deliveries are included in Full or excluded from the retained view. |

The timing selector switches between Full and ≤1,440 minutes. The server caches successful results for up to two minutes per workbook and timing selection. Missing rates display as unavailable, and connection failures produce a generic message without replacement values. Counts and denominators are visible as text as well as through chart tooltips. The orange chart segment marks late arrivals. Neutral slate tones and distinct markers differentiate the address groups.

The figures are observational. Standardization covers supported strata only. The timing cutoff can exclude valid long routes. Early arrival can reflect waiting before service, and the workbook supplies route-relative minutes. Geodesic kilometers describe straight-line geometry.

## Launch from Ubuntu WSL

Prerequisites are the Task 014 views, the Task 015 virtual environment, and the private passfile at `~/.config/p002/pgpass`. The existing [Task 015 setup instructions](015_Streamlit_Smoke_Runbook.md) document dependency installation and credentials. Page 1 uses Streamlit and Psycopg from that environment and Streamlit's installed Altair and pandas dependencies.

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run executive_overview.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --theme.base light --theme.primaryColor '#58758C' --theme.textColor '#182431'
```

Open `http://127.0.0.1:8501` in the Windows browser. Use Ctrl+C to stop any existing smoke app on port 8501 first. Check that the full cohort shows **11.13% late deliveries**, **43.27% routes with late arrivals**, **47.94 minutes median** with **206.09 minutes P90**, and **73.18% changed address order**. Select the retained cohort and confirm **21,748 / 201,796** eligible deliveries and **7,771 / 18,238** eligible routes on the two late-rate cards. Confirm the audit readout says the long-span routes were excluded.

## QA commands

```bash
# Run from the repository root.
.venv/bin/python -B 05_Quality_Assurance/Tests/test_executive_overview.py -v
.venv/bin/python -B 05_Quality_Assurance/Tests/test_dashboard_smoke.py -v
```

To include the live PostgreSQL assertion in normal WSL, run:

```bash
# Run from the repository root.
env -u PGPASSWORD P002_EXECUTIVE_LIVE=1 \
  .venv/bin/python -B 05_Quality_Assurance/Tests/test_executive_overview.py -v
```

### Observed QA

Six automated data and Streamlit rendering tests passed. They covered approved view and role selection, the read-only snapshot, KPI and chart rendering, both timing selections, unavailable comparisons, and redacted connection errors. Three existing smoke-app tests also passed. The opt-in live login tests were skipped in this session.

The Page 1 query projections ran for both cohorts against the verified full extract in disposable PostgreSQL 18.6 as `p002_report`. They matched the expected route, eligible-delivery and late-delivery counts and six supported strata for each timing cohort. The sandbox denied loopback binds and database connections, so Windows browser layout and live role authentication remain to be checked with the normal WSL commands above.

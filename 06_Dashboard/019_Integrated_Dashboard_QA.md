# Integrated dashboard QA and presentation

**P002 · Task 019 · Three-page local Streamlit dashboard**

The dashboard uses one sidebar timing selection across its three pages. Page 2 and Page 3 retain page-local filters, reset the review page on scope changes, and use bounded route-level queries. Route and visit detail stay at their approved grains. [Architecture](014_Dashboard_Architecture.md) · [Data contract](014_Dashboard_Data_Contract.md)

## Presentation changes

- Route search tables use short cohort and exception columns. An expandable selection preserves visit-order metrics. The visit drill keeps position, stop, address, outcome, late minutes and flags in view. Its expandable detail separates offset and eligibility tables, both keyed by actual position.
- Distance review shows category, signed geodesic change and review flags at a glance. The selected route's expandable detail shows planned, actual, signed and absolute geodesic kilometers, plus the percentage change from planned. Zero planned distance remains unavailable for the percentage.
- P05, median and P95 use separate labeled rows on a signed geodesic kilometer axis with a zero reference. Percentage axes and relative-minute columns carry units. Routes and deliveries have separately labeled denominators.
- The integrated layout stacks columns at widths up to 720 px. Charts use container width and text equivalents for rates and sample sizes. Changed and unchanged markers use distinct shapes, and flags have text labels. The approved slate-blue and burnt-orange palette remains in use.
- Empty selections, missing measurements and connection failures display distinct messages. Connection errors omit raw database details. SQL projections, approved eligibility definitions, statistics, and denominators are unchanged.

## Normal WSL verification

Run the automated suite with live read checks enabled using the existing Task 015 passfile. The reporting role check prints only the current role, transaction read-only status and schema privilege booleans. Expect `p002_report`, `on`, and `false` for both restricted schemas.

```bash
# Run from the repository root.
env -u PGPASSWORD P002_SMOKE_LIVE=1 P002_EXECUTIVE_LIVE=1 P002_ROUTE_LIVE=1 P002_DISTANCE_LIVE=1 \
  .venv/bin/python -B -m unittest discover -s 05_Quality_Assurance/Tests -p 'test_*.py' -v
env -u PGPASSWORD PGPASSFILE="$HOME/.config/p002/pgpass" \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_report -d p002_last_mile \
  -c 'BEGIN READ ONLY;' \
  -c "SELECT current_user, current_setting('transaction_read_only'), has_schema_privilege('core','USAGE'), has_schema_privilege('staging','USAGE');" \
  -c 'ROLLBACK;'
```

Launch the dashboard using the existing environment and private passfile. [Environment setup](015_Streamlit_Smoke_Runbook.md)

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run dashboard.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --theme.base light --theme.primaryColor '#58758C' --theme.textColor '#182431'
```

Open `http://127.0.0.1:8501` in Windows and verify:

1. Full overview late rates show 11.13% of eligible deliveries and 43.27% of eligible routes. Change timing to retained and navigate through Pages 2 and 3 and back. The sidebar choice should persist.
2. On Page 2 change country and size, then paginate or search. Confirm the displacement chart remains pooled by country and size. Select a route and expand its sequence and visit details. Check keyboard focus, labels, and table scrolling.
3. On Page 3 restore Full and clear the cohort filters. Confirm 7,386 shorter, 5,291 equal, 6,970 longer, 98 distance-review routes, and P05 / median / P95 of −17.77 / 0.00 / +11.60 geodesic km. Search route 7545 under Distance review and confirm the nonzero actual same-address leg flag. Test the layout at desktop and narrow widths, including readable quantile labels and keyboard access to the controls.

## Sandbox verification

```bash
# Run from the repository root.
.venv/bin/python -B -m unittest discover -s 05_Quality_Assurance/Tests -p 'test_*.py'
.venv/bin/python -B 05_Quality_Assurance/Tests/dry_run_dashboard_contract.py \
  02_Data_Processed/task008_routes_staging.csv
.venv/bin/python -B 05_Quality_Assurance/Tests/dry_run_consolidated_qa.py \
  02_Data_Processed/task008_routes_staging.csv
```

### Results and remaining checks

Twenty-six tests passed and four opt-in live checks were skipped. Streamlit rendering tests exercised all three pages, shared timing, filter scope, pagination, inspection transitions, labeled quantile chart encoding, and error redaction. The disposable dashboard contract verified 249,231 visits, 19,647 routes, and all three timing cohorts. The reporting role read all three dashboard contract views, and their grant checks passed.

The session denied the PostgreSQL Unix socket and creation of a localhost listener. Live authentication, browser behavior at narrow widths, keyboard focus order, and assistive-technology behavior remain normal-WSL checks. The automated tests cover labels and visible alternatives to chart color without simulating those browser interactions.

The separate consolidated analytical QA also passed. It reconciled the approved workbook KPIs, standardization and distance statistics, and exercised read access to the 11 underlying analytical views as the reporting role. [Consolidated analytical QA](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

# Distance Deviations & Data Quality

**P002 · Task 018 · Page 3**

The [Page 3 app](distance_quality.py) uses the shared sidebar timing control in the [three-page dashboard](dashboard.py). It also exposes country, size, and address order. [Approved data contract](014_Dashboard_Data_Contract.md) · [Wireframe](014_Dashboard_Wireframes.md)

| Section | Approved data and filter scope |
|---|---|
| Category counts and late outcomes | `reporting.route_distance_comparison`. Select only the rows for the chosen timing, country, size, and address scope. The chart reports shorter, equal, longer, and missing if present. The late-route denominator is routes with eligible deliveries. The late-delivery denominator is eligible deliveries. Visible counts accompany rates. |
| Signed-change P05, median and P95 | The null-category rollup from the same selected scope. Percentiles come from PostgreSQL and are never combined across category rows. |
| Timing and distance review | `reporting.dashboard_route`, at route grain, with exact numeric ID search and local category and flag filters. The default requires a timing or distance review flag. Select **All routes** to look up an unflagged route. Sorting uses distance review, absolute change, route ID, and import ID. There are 25 displayed rows per page with a single extra row fetched to determine if another page exists. |
| Route inspection | The selected route's existing row supplies planned, actual, signed, absolute and percentage changes and flags. An unavailable percent is shown for zero planned distance. Changing the table filters resets the page and selection. |

The [reader](distance_quality_data.py) uses bound parameters and the dashboard's existing loopback, read-only `p002_report` connection. Route counts are never joined to visit rows. Timing review covers arrival reversal and timing span above 1,440 minutes. Distance review includes recorded same-address nonzero legs, zero planned totals, missing totals, and absolute gaps of at least 100 km. Flags remain visible without changing KPI eligibility. The retained timing cohort excludes long-span routes from both sections.

Distance measures sum straight-line Haversine legs. Road mileage and operating costs require separate measurements. The rate comparisons are observational and remain sensitive to route mix and timing quality.

## Launch and verify in normal Ubuntu WSL

Use the Task 015 environment and private passfile. Stop an older Streamlit process on port 8501 with Ctrl+C. [Environment and credentials](015_Streamlit_Smoke_Runbook.md)

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run dashboard.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --theme.base light --theme.primaryColor '#58758C' --theme.textColor '#182431'
```

Open `http://127.0.0.1:8501` in Windows and select **Distance Deviations & Data Quality**. In Full with All filters, confirm **7,386 shorter**, **5,291 equal**, **6,970 longer**, **98 distance-review routes**, and **0.00 km median**. Switch timing to retained and confirm the scoped count is **18,479**. Return to Full, choose **Distance review**, search **7545**, and inspect the route. The flags should include a nonzero actual same-address leg.

Run the [automated tests](../05_Quality_Assurance/Tests/test_distance_quality.py) and opt-in live assertions from the project root.

```bash
# Run from the repository root.
.venv/bin/python -B -m unittest discover -s 05_Quality_Assurance/Tests -p 'test_*.py'
env -u PGPASSWORD P002_DISTANCE_LIVE=1 \
  .venv/bin/python -B 05_Quality_Assurance/Tests/test_distance_quality.py -v
```

## Observed QA

The full suite ran 29 tests. Twenty-five passed and four opt-in live PostgreSQL checks were skipped. Page 3 tests covered bound filters, grouping grain, table pagination, route inspection, zero-denominator display, chart rendering, and shared timing navigation. Prepared Page 3 statements also passed against the verified extract on disposable PostgreSQL 18.6 as `p002_report`. They matched the full baseline, exercised retained and filtered summaries and two bounded review pages, and found the recorded anomaly on route 7545. The live Unix socket was denied in this session. The normal-WSL commands above cover live authentication and Windows browser verification.

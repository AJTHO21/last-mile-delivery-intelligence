# PostgreSQL dashboard data contract

**Task 014 · Contract version 1 · PostgreSQL 18.6**

Workbook v1 is the published snapshot. Read these views as `p002_report`. Numeric precision remains in SQL. Rates are proportions unless explicitly named `_pct` or `_pp`. Display percentages to two decimals, distances in geodesic km, and times in route-relative minutes. Render unknown or zero-denominator rates as “Unavailable”. [Provenance](../08_Documentation/Dataset_Provenance.md) · [Approved definitions](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

## Datasets and keys

| Dataset in `reporting` | Grain and key | Consumers |
|---|---|---|
| `dashboard_overview` | One row per timing cohort. Timing cohort is text and is the key. | Page 1 cards and window distribution. Removed audit readout selects its own partition. |
| `dashboard_route` | One row per route. Join on integer `route_id` and bigint `import_id`. Includes country, size, sequence metrics, timing flags, delivery outcomes, and geodesic measures. | Pages 2 and 3 filtered route tables and route selection. |
| `dashboard_visit` | One row per source visit. Key is bigint `import_id`, text `worksheet_name`, integer `source_row_number`. Route and planned index are alternative identifiers on typed visits. Includes two positions, IDs, stop flags, relative window values, class, eligibility reason, durations, and timing flags. | Page 2 route drill-through. Rows missing a typed visit remain in this dataset by lineage. |
| `route_performance_comparison` | One row per timing cohort and country/size grouping level, with separate changed and unchanged counts. | Pages 1 and 2 crude comparisons. |
| `route_performance_standardized` and `route_performance_standardization_strata` | Summary keyed by timing cohort. Strata additionally keyed by country and size. | Page 1 fixed-cohort standardized comparison, support badge, and sparse-strata detail. |
| `visit_displacement_lateness` | Timing cohort × address status × visit-order status × displacement band. | Page 2 displacement sample sizes and rates. |
| `route_distance_comparison` | Timing cohort × country × size × address-order status × distance category, including marginal rollups. | Page 3 category counts, lateness rates, and distance quantiles. |

Three new views are defined in [version 014 SQL](../03_SQL/03_Analysis/014_Dashboard_Data_Contract.sql). Earlier reporting views remain the reference for approved semantics. The three new views contain no driver field. Use parameter binding for values. Query selected datasets independently, then associate records in the UI by stable keys. Joining visits into a route summary before aggregation would duplicate route measures.

## Measures and denominators

| Metric | Contract |
|---|---|
| Early, in-window, late arrivals | Counts divided by eligible delivery visits. Eligibility is a non-depot delivery with valid timing. Early is before earliest, late is after latest, and both boundaries are included in-window. Early can reflect waiting. |
| Lateness severity | Median and P90 of arrival minus latest among eligible late visits. Use overview values for the selected cohort. Route drill shows individual late minutes and early minutes where applicable. |
| Routes with any late arrival | Late routes divided by routes with at least one eligible delivery. Detailed route delivery rate uses its own eligible visits. Results use separate route and delivery labels. |
| Changed address order | Routes with verified changed full address sequence divided by routes with valid sequences. Exact visit order compares occurrence positions independently. |
| Visit movement | Moved count and percent use visits on the route. Absolute displacement is the magnitude of planned minus actual position. Displacement panel late rate is late eligible deliveries divided by eligible deliveries in that cell. Distinct route counts can recur across cells. |
| Crude comparison | Changed and unchanged rates use their observed denominators. Rate gaps are changed minus unchanged in percentage points. |
| Standardized comparison | Fixed country × size weights from pooled eligible routes in supported strata, recomputed per timing cohort. Both groups must have at least 50 eligible routes and 100 eligible visits. The delivery endpoint is a delivery rate within each stratum averaged over the common route distribution. Show the eligible-route coverage and supported/observed strata. |
| Geodesic difference | Sum all recorded planned/actual legs at route grain. Signed is actual minus planned, absolute is magnitude, percentage divides by planned and returns null at zero. The inclusive ±1e-9 km band is equal. Quantiles describe the distribution of paired signed route differences. |
| Review flags | Timing span >1,440 minutes, arrival tie/reversal, zero-width window, overlap of depot/delivery, and large visit timing gaps retain their existing fields. The route distance review flag covers zero planned, missing legs, nonzero consecutive same-address legs, and absolute gaps ≥100 km. Counts include flagged observations whenever they are in the selected timing cohort. |

Distance and arrival outcome relationships are observational. Straight-line Haversine leg sums describe recorded route geometry. Road mileage, driving time and cost require separate data.

## Filter semantics and query rules

- **Timing.** Match `full` or `span_at_most_1440` explicitly on aggregate views. Use `removed_over_1440` only for the audit readout. In route detail the retained cohort is `NOT route_timing_span_over_1440`. Bubble the selected route scope into visit drill-through rather than refiltering visit rows.
- **Country and size.** Country is 0 Norway and 1 Denmark. Size counts all visits including depots and repeats. Bands are 1–5, 6–10, 11–20, and 21+. For a rollup row bind `NULL` for an All dimension and use `column IS NOT DISTINCT FROM parameter`. For route detail, null means no predicate on that dimension.
- **Address status.** Changed, unchanged, or unverified. Page 2 comparison keeps both verified groups visible. Page 3 address selector selects the rollup or matching category in `route_distance_comparison`. For category charts use rows with individual distance categories. For overall quantiles and denominator cards select the null distance-category rollup. Counts and rates from different grouping levels must never be added together.
- **Fixed comparisons.** Page 1 crude uses both country and size rollups. Standardized data uses the selected timing cohort only. Displacement likewise uses timing plus its own address-order and visit-order controls. Labels make these scopes visible. Percentiles and standardized percentages are never averaged across chart cells.
- **Details.** Use a parameterized route lookup and stable sort with the route and import keys as tie-breakers. Limit routes to 25 per page. Retrieve a selected route's visits by both route keys and sort by `index_a` to show recorded actual order. Include `index_p` alongside it. Retain all visit rows for the route and show why a row is ineligible.
- **Exceptions.** Separate late outcome, timing flags, and distance review flags. Keep the category and review filters local to the relevant detail table. Reset route selections outside the current scope. Show zero-count or empty states without reusing a denominator from another cohort.

## Verification and deployment

The [read-only contract QA](../05_Quality_Assurance/Tests/Verify_P002_Dashboard_Contract.sql) validates grain, drill-through cardinality, approved full and sensitivity counts, a filtered rollup, fixed standardization coverage, and reporting grants. The [disposable harness](../05_Quality_Assurance/Tests/dry_run_dashboard_contract.py) loads the verified local CSV, creates the approved dependencies, and exercises all three new views as the reporting role.

```bash
# Run from the repository root.
python3 -B 05_Quality_Assurance/Tests/dry_run_dashboard_contract.py \
  02_Data_Processed/task008_routes_staging.csv
```

For the build phase, deploy from the normal Ubuntu WSL terminal with the existing development login and password prompt:

```bash
# Run from the repository root.
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/03_Analysis/014_Dashboard_Data_Contract.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Dashboard_Contract.sql
```

## Observed QA results

The disposable PostgreSQL 18.6 run exited 0 and returned `P002 dashboard data contract passed`. The reporting role read all three datasets. Drill-through preserved all 249,231 visits. The scoped Norway × 11–20 visits × changed-address × retained rollup matched route detail, and the full standardization view matched six supported strata and 17,617 of 19,383 covered eligible routes.

| Timing cohort | Source visits | Routes | Eligible deliveries | Late deliveries | Eligible routes | Late routes |
|---|---:|---:|---:|---:|---:|---:|
| Full | 249,231 | 19,647 | 213,122 | 23,718 | 19,383 | 8,387 |
| Retained | 234,689 | 18,479 | 201,796 | 21,748 | 18,238 | 7,771 |
| Removed | 14,542 | 1,168 | 11,326 | 1,970 | 1,145 | 616 |

The approved full-cohort outcome counts and late percentiles matched. The session could not reach the host database. Deploy and rerun QA from normal WSL during the build phase. Browser rendering, runtime dependency installation, and the Windows Power BI connector remain build-phase checks.

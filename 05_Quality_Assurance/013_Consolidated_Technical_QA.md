# Consolidated technical QA

**Phase 5 · Task 013 · PostgreSQL 18.6**

The handoff confirms that Tasks 007–012 were deployed and verified, including Task 012 exit status 0. This session was denied access to the live Unix socket and could not connect over loopback. Task 013 uses the full verified workbook extract in disposable PostgreSQL. [Task 012 live status and evidence](../08_Documentation/PostgreSQL_Route_Distance_Analytics.md)

## Scope and final definitions

| Area | Contract |
|---|---|
| Source and lineage | Mendeley workbook v1, one import, `Sheet1` Excel rows 2–249,232. Source and typed visit join on import, worksheet, and source row. All 16 typed fields reconcile, including route-level country and driver. |
| Visit and route grain | Visit key is route plus planned position. Actual position is also unique within the route. Route outcomes are aggregated before joining across views. Stop and address codes can repeat. |
| Arrival | Eligible visits are non-depot deliveries with structurally valid offsets. Window boundaries are inclusive. Late means strictly after the latest offset. Route late rates use routes with eligible deliveries. Median and P90 use only eligible late visits. |
| Sequence | Recorded planned and actual positions determine order. The exact visit test compares occurrence order. The address test compares ordered sequences retaining duplicates. |
| Distance | Sum recorded Haversine legs, including depots. Signed change is actual minus planned, absolute change is its magnitude, and percentage change is null at zero planned distance. Equal covers absolute gaps ≤1e-9 km. Review includes zero planned distance, nonzero consecutive same-address legs, missing totals, and gaps of at least 100 km. |
| Timing sensitivity | The route span is the maximum minus minimum across recorded arrival and window offsets. Show full, retained ≤1,440 minutes, and removed >1,440 minutes separately. |
| Standardization | For each timing cohort, require both address groups in a country/size stratum to have ≥50 eligible routes and ≥100 eligible deliveries. Weight supported strata by their pooled eligible-route counts normalized across supported strata. Use the same weights for both groups and endpoints. The standardized delivery endpoint uses within-stratum visit rates under this common route distribution. |
| Access | `p002_report` can select from the 11 approved reporting views. QA checks that it lacks staging and core schema access and exercises reads as that role in the disposable database. |

The [consolidated SQL entry point](Tests/013_Consolidated_Analytical_QA.sql) reuses the four existing read-only analytical QA scripts, then independently recomputes source lineage, principal counts, severity and distance statistics, and country/size standardization from staging and core. Each check group uses a read-only transaction. The consolidated calculation uses a repeatable-read snapshot. Execute while ingestion and schema changes are idle so the separate check groups see a consistent version. The [standalone dry-run harness](Tests/dry_run_consolidated_qa.py) builds a disposable copy, loads the verified extract, deploys the migrations, then runs those checks and queries all reporting views as `p002_report`.

## Normal WSL verification

Place the official workbook in `01_Data_Raw/`. The file check verifies original workbook and existing extract bytes. SQL independently verifies the registered import identity and staging-to-core parity. The same versioned script should return `P002 consolidated analytical QA passed` and exit status 0.

```bash
# Run from the repository root.
printf '%s  %s\n' \
  8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00 01_Data_Raw/routes_performance.xlsx \
  1aa8609bf2539f191d4d43c9be7fbf5ad3926b055239c70fee6eb383e6f20273 02_Data_Processed/task008_routes_staging.csv |
  sha256sum --check --strict &&
  psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
    -f 05_Quality_Assurance/Tests/013_Consolidated_Analytical_QA.sql
```

Use the existing login password at the interactive prompt. Exercise the live reporting login independently with:

```bash
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_report -d p002_last_mile \
  -c 'SELECT eligible_delivery_count, late_count FROM reporting.arrival_window_summary;' \
  -c 'SELECT count(*) FROM reporting.route_distance;'
```

Run the disposable verification without a live connection:

```bash
python3 -B 05_Quality_Assurance/Tests/dry_run_consolidated_qa.py \
  02_Data_Processed/task008_routes_staging.csv
```

## Observed test results

The disposable PostgreSQL 18.6 run exited 0, reached the consolidated success marker, and returned results from all 11 views as `p002_report`. Both local SHA-256 checks matched. The lineage check found zero mismatched rows across all 16 fields. The prior boundary fixture uses temporary synthetic writes and is outside the consolidated read-only suite. Snapshot checks cover actual classifications, anomaly cases, and view-to-detail reconciliation.

| Independent control | Observed |
|---|---:|
| Source records | 249,231 |
| Routes | 19,647 |
| Eligible deliveries | 213,122 |
| Late deliveries | 23,718 |
| Early arrivals | 24,252 |
| In-window arrivals | 165,152 |
| Changed visit-order routes | 15,067 |
| Moved visits | 124,310 |
| Routes with eligible deliveries | 19,383 |
| Routes with late arrivals | 8,387 |
| Shorter routes | 7,386 |
| Equal-distance routes | 5,291 |
| Longer routes | 6,970 |
| Distance review routes | 98 |

Independent recomputation matched total planned and actual geodesic distance of 1,260,561.50 and 1,241,690.34 km. The paired signed gap P05, P50, and P95 were −17.77, 0.00, and +11.60 km. Lateness P50 and P90 were 47.94 and 206.09 minutes among 23,718 eligible late deliveries.

| Cohort | Supported strata | Pooled eligible routes covered | Crude route gap | Standardized route gap | Crude delivery gap | Standardized delivery gap |
|---|---:|---:|---:|---:|---:|---:|
| Full | 6/8 | 17,617/19,383 (90.89%) | +9.37 pp | −0.15 pp | −4.08 pp | −3.02 pp |
| Timing retained | 6/8 | 16,597/18,238 (91.00%) | +10.13 pp | +0.02 pp | −3.48 pp | −2.73 pp |

Differences are changed minus unchanged address order. The independent computation checked each stratum's denominators, support, and weight, and both weighted endpoints. The two excluded strata were the 21+ visit band in Norway and Denmark in both timing cohorts. They remained in crude analysis. The timing partition removed 1,168 routes, 11,326 eligible deliveries and 1,970 late deliveries. The retained cohort contained 18,479 routes, 201,796 eligible deliveries and 21,748 late deliveries. [Full strata and sensitivity evidence](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

## Discrepancies and evidence limits

- The tested workbook snapshot produced zero mismatches against approved KPI controls. The Phase 0 source discrepancy persists in documentation. The workbook contains 19,647 routes, 150 more than the data descriptor's 19,497 route pairs. The reason for the lower descriptor count is unresolved. [Phase 0 evidence](Phase_0_Evidence/P002_Dataset_Feasibility_Report.md)
- Workbook and extract hashes are checked at the file boundary. The SQL suite checks registered metadata and staging-to-core parity. The disposable load tested those files end to end, while repeating Task 013 against the live host remains pending.
- The checks establish reconciliation of recorded values and report definitions. They cannot establish whether timing outliers reflect clock issues or valid long operations, validate road travel, or identify causal drivers of lateness.

# Route sequence deviation analytics

**Phase 4, Task 010 · PostgreSQL 18.6**

Task 009 live deployment and QA passed per the handoff. The arrival-window detail provides eligibility and late-arrival classifications for this task. [Task 009 evidence](PostgreSQL_Arrival_Window_KPIs.md)

## Methodology

| View | Grain and measures |
|---|---|
| `reporting.visit_sequence_deviation` | One row per `(route_id, index_p)`. Retains the visit lineage, both positions, stop and address codes, and depot flag. A moved visit has unequal indices. Absolute displacement is the unsigned difference in positions. Each predecessor is represented by its planned index as a stable visit identifier. |
| `reporting.route_sequence_deviation` | One row per core route. Compares the complete ordered arrays of planned visit identifiers and of address codes, each reconstructed once in planned order and once in actual order. Reports moved count, percentage of visits moved, and total, mean, and maximum absolute displacement across all visits. |
| `reporting.route_sequence_lateness_summary` | Reports route and visit sample sizes, eligible route counts, late route counts, and late route proportions, overall and by address change, country, route size, and their combinations. A null country or band represents an aggregate across that dimension. The address status `all` represents a rollup across address-sequence statuses. |

The visit view uses `LAG` in two windows over the recorded indices. The ordered arrays keep every occurrence, including repeated Stop IDs, repeated Address IDs, and depot visits. An exact visit match can differ from an exact address match when visits at the same location are swapped. Route position validity uses the schema's two uniqueness keys and verifies consecutive zero-based indices. Routes with an incomplete sequence remain visible with null exact-match flags and an `unverified` summary status.

Route size counts every visit. The chosen bands are 1–5, 6–10, 11–20, and 21+ visits. A parent with no visits would appear in band 0. Country code 0 is Norway and 1 is Denmark. The late-route denominator is the number of routes with at least one eligible delivery, and the numerator is the number of those routes with at least one eligible late arrival. The proportion is null for an empty denominator. The arrival view is grouped by route and import before joining the route view, so the join cannot multiply visit or route counts.

Timing flags for arrival reversal and timing spans above 24 hours remain visible at route grain. The baseline uses all eligible visits. A route with more deliveries has more opportunities to record at least one late arrival. Country and size bands describe differences in the observed mix. They do not establish why arrivals were late.

## Deployment and reproducibility

Run the [version 010 migration](../03_SQL/03_Analysis/010_Route_Sequence_Views.sql) and [read-only QA](../05_Quality_Assurance/Tests/Verify_P002_Route_Sequence.sql) in an ordinary Ubuntu WSL terminal after Task 009. Use the existing development login at the password prompt.

```bash
# Run from the repository root.
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/03_Analysis/010_Route_Sequence_Views.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Route_Sequence.sql
```

The migration creates or replaces the three views in a transaction and grants SELECT to the reporting role. The QA compares view grain and lineage to core, checks both predecessor sequences, verifies the complete address arrays and exact-match flags, checks repeated-code counts, and reconciles the lateness comparison to the detail.

The Task 011 handoff confirms that Task 010 deployed successfully and live QA passed in the normal WSL terminal. The disposable verification evidence remains below. Reproduce the disposable test using the local Task 008 CSV and installed PostgreSQL 18 binaries:

```bash
python3 -B 05_Quality_Assurance/Tests/dry_run_route_sequence.py \
  02_Data_Processed/task008_routes_staging.csv
```

## Observed QA results

The migration ran twice on disposable PostgreSQL 18.6. Read-only QA passed against the full verified extract, and the reporting role successfully queried all three views. The results matched all seven Phase 0 reconciliation counts. The views also retained 6,622 routes with repeated Stop IDs, 10,961 with repeated addresses, and 689 whose visit order changed while their address order matched.

| Reconciliation metric | Observed |
|---|---:|
| Routes | 19,647 |
| Exact visit-order matches | 4,580 |
| Exact address-order matches | 5,269 |
| Changed visit-order routes | 15,067 |
| Moved visits | 124,310 |
| Routes with an eligible delivery | 19,383 |
| Routes with an eligible late arrival | 8,387 |

The table reports late routes over eligible routes for each cohort. Rates are rounded for display.

| Cohort | All address sequences | Unchanged address sequence | Changed address sequence |
|---|---:|---:|---:|
| Overall | 8,387 / 19,383 (43.27%) | 1,862 / 5,119 (36.37%) | 6,525 / 14,264 (45.74%) |
| Norway | 3,641 / 8,190 (44.46%) | 1,284 / 3,698 (34.72%) | 2,357 / 4,492 (52.47%) |
| Denmark | 4,746 / 11,193 (42.40%) | 578 / 1,421 (40.68%) | 4,168 / 9,772 (42.65%) |
| 1–5 | 394 / 1,703 (23.14%) | 285 / 1,283 (22.21%) | 109 / 420 (25.95%) |
| 6–10 | 1,749 / 5,643 (30.99%) | 796 / 2,326 (34.22%) | 953 / 3,317 (28.73%) |
| 11–20 | 5,115 / 10,271 (49.80%) | 735 / 1,452 (50.62%) | 4,380 / 8,819 (49.67%) |
| 21+ | 1,129 / 1,766 (63.93%) | 46 / 58 (79.31%) | 1,083 / 1,708 (63.41%) |

The pooled late-route rate is higher for changed address sequences, but the direction reverses in three of the four size bands. In the 21+ band, the unchanged comparison has only 58 eligible routes. The size mix and uneven sample sizes limit interpretation of the pooled gap.

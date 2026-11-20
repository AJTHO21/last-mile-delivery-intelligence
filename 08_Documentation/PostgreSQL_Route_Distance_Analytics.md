# Planned versus actual route distance analytics

**Phase 4, Task 012 · PostgreSQL 18.6**

The Task 012 handoff reports that Task 011 live deployment and verification completed with PostgreSQL exit status 0. [Task 011 verification evidence](PostgreSQL_Route_Performance_Comparisons.md)

## Methodology

- `reporting.route_distance` holds one row per route. It sums the workbook's recorded planned and actual Haversine legs across every core visit, including first-position zero legs, depots, repeated stops, and repeated addresses. The existing route-level reporting view supplies visit counts, country, size band, exact address-order status and arrival-window outcomes. Distance and outcome facts meet on the route and import keys after aggregation.
- Signed difference is actual minus planned kilometers. Absolute difference is its magnitude. Percentage difference is 100 times signed difference divided by planned kilometers. A zero planned total yields a null percentage and remains visible. A route without recorded legs would have a missing distance category.
- The shorter and longer categories require a signed gap below −0.000000001 km or above +0.000000001 km. Values within those inclusive bounds are equal, matching the Phase 0 tolerance. The exact numeric sums are preserved.
- `reporting.route_distance_comparison` provides counts, totals, distribution statistics, and lateness rates by country, route size, address-order status, and distance category, including intersections and rollups. Null dimension values identify rollups. The unweighted mean percentage difference uses only routes with positive planned totals. Continuous percentiles use PostgreSQL's floating-point interpolation.
- Late-delivery rate divides late eligible visits by eligible delivery visits. Late-route rate divides routes with any eligible late arrival by routes with at least one eligible delivery. Size bands are 1–5, 6–10, 11–20, and 21+ visits. These comparisons use the original arrival-window eligibility rules. [Charter](../00_Admin_and_Scope/Project_Charter.md) · [Arrival-window definitions](PostgreSQL_Arrival_Window_KPIs.md) · [Phase 0 evidence](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md)

### Sensitivity and anomaly flags

The `full` cohort contains all routes. `span_at_most_1440` excludes routes whose timing span exceeds 1,440 minutes, and `removed_over_1440` exposes the omitted counts. Distances and route order are preserved in every cohort.

Distance review flags identify missing legs at route level, a zero planned total, nonzero legs between consecutive identical address codes, and absolute route gaps of at least 100 km. The 100 km threshold is an exploratory review choice. Ordered windows identify the predecessor independently for each sequence. Flags remain visible in the detail and contribute to summary counts. No distance-based exclusions are applied.

## Deployment and independent QA

Run the [migration](../03_SQL/03_Analysis/012_Route_Distance_Analytics.sql) and [read-only verification](../05_Quality_Assurance/Tests/Verify_P002_Route_Distance.sql) after Task 010 is available. The migration adds two views and SELECT grants for the reporting role.

```bash
# Run from the repository root.
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/03_Analysis/012_Route_Distance_Analytics.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Route_Distance.sql
```

Use the existing role password at the prompt. The Task 013 handoff confirms that Task 012 deployed on the live PostgreSQL 18.6 cluster and its verification returned exit status 0.

QA checks each core leg against the original staging value, reconstructs predecessor anomalies independently using adjacent indices, and checks route totals, grain, arrival outcomes, zero denominators, and classification. It independently expands routes across all 16 dimension rollups to reconcile counts and additive totals. It also checks both view grants and exclusion of direct staging/core access.

Reproduce the disposable test against the verified Task 008 CSV and installed PostgreSQL 18 binaries.

```bash
python3 -B 05_Quality_Assurance/Tests/dry_run_route_distance.py \
  02_Data_Processed/task008_routes_staging.csv
```

## Verified results

PostgreSQL 18.6 ran the migration twice on the full verified extract. Read-only QA passed across 19,647 routes and 249,231 visits, and the reporting role queried both views. Phase 0 direction counts, zero-planned count, and the recorded same-address anomaly all reconciled.

Total planned distance was **1,260,561.50 geodesic km** and total actual distance was **1,241,690.34 geodesic km**. Median route totals were **50.08 planned** and **49.03 actual**. The median paired change was **0.00 km**, with P05 -17.77 km and P95 11.60 km. The unweighted mean percentage change was -0.12% across 19,646 routes with positive planned totals.

| Timing cohort | Routes | Visits | Eligible deliveries | Late deliveries | Distance review routes |
|---|---:|---:|---:|---:|---:|
| Full | 19,647 | 249,231 | 213,122 | 23,718 | 98 |
| Retained at ≤1,440 minutes | 18,479 | 234,689 | 201,796 | 21,748 | 69 |
| Removed above 1,440 minutes | 1,168 | 14,542 | 11,326 | 1,970 | 29 |

The largest signed differences were -507.11 km and +1,898.70 km. Of 98 distance review routes, 96 met the 100 km screen. One route had zero planned distance. Route 7545 contained the single nonzero actual leg between consecutive occurrences of the same address code. No planned leg had that condition.

### Distance category and late arrivals

Each outcome cell shows late / eligible. The three categories partition each timing cohort.

| Timing cohort | Distance category | Routes | Late routes | Late deliveries |
|---|---|---:|---:|---:|
| Full | Shorter | 7,386 | 3,350/7,325 (45.73%) | 9,032/89,937 (10.04%) |
| Full | Equal | 5,291 | 1,872/5,140 (36.42%) | 5,343/36,793 (14.52%) |
| Full | Longer | 6,970 | 3,165/6,918 (45.75%) | 9,343/86,392 (10.81%) |
| Retained | Shorter | 7,030 | 3,172/6,972 (45.50%) | 8,528/86,024 (9.91%) |
| Retained | Equal | 4,967 | 1,704/4,835 (35.24%) | 4,818/35,245 (13.67%) |
| Retained | Longer | 6,482 | 2,895/6,431 (45.02%) | 8,402/80,527 (10.43%) |

### Country, size, and address-order comparisons

The full-cohort marginal results below pool the other dimensions. The comparison view also exposes intersections, distance categories, and both timing partitions.

| Cohort | Routes | Median planned / actual km | Paired signed difference P05 / median / P95 km | Late routes | Late deliveries |
|---|---:|---:|---:|---:|---:|
| Norway | 8,438 | 65.52 / 64.29 | -20.88 / 0.00 / 12.11 | 3,641/8,190 (44.46%) | 10,051/72,232 (13.91%) |
| Denmark | 11,209 | 40.34 / 39.75 | -16.34 / 0.00 / 11.43 | 4,746/11,193 (42.40%) | 13,667/140,890 (9.70%) |
| 1–5 visits | 1,842 | 62.05 / 61.45 | -9.36 / 0.00 / 4.64 | 394/1,703 (23.14%) | 730/4,741 (15.40%) |
| 6–10 visits | 5,753 | 53.23 / 52.00 | -16.37 / 0.00 / 8.83 | 1,749/5,643 (30.99%) | 4,050/36,758 (11.02%) |
| 11–20 visits | 10,286 | 46.58 / 45.92 | -19.17 / 0.00 / 13.13 | 5,115/10,271 (49.80%) | 14,671/135,318 (10.84%) |
| 21+ visits | 1,766 | 50.72 / 50.54 | -19.53 / 0.00 / 16.42 | 1,129/1,766 (63.93%) | 4,267/36,305 (11.75%) |
| Unchanged address order | 5,269 | 61.62 / 61.60 | 0.00 / 0.00 / 0.00 | 1,862/5,119 (36.37%) | 5,325/36,699 (14.51%) |
| Changed address order | 14,378 | 46.38 / 45.49 | -24.26 / -0.02 / 15.09 | 6,525/14,264 (45.74%) | 18,393/176,423 (10.43%) |

### Interpretation and limits

The shorter and longer categories had nearly identical full-cohort late-route rates. Equal-distance routes had the lowest late-route rate and the highest late-delivery rate in both timing cohorts. A route with more eligible deliveries has more chances to record at least one late arrival. The two rates capture different aspects of delivery performance and their pooled comparisons depend on route composition.

The recorded values are sums of straight-line Haversine legs between recorded locations. Road mileage, fuel use, driving time, and road-network performance require separate measurements. These descriptive comparisons are sensitive to route mix, repeated locations, and timing anomalies. They provide no estimate of a causal effect of resequencing.

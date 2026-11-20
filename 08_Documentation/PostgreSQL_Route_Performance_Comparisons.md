# Route performance comparisons and sensitivity

**Phase 4, Task 011 · PostgreSQL 18.6**

The Task 011 handoff confirms successful Task 010 live deployment and QA. Its verification evidence remains in the [route sequence runbook](PostgreSQL_Route_Sequence_Analytics.md). Task 011 follows the [charter](../00_Admin_and_Scope/Project_Charter.md), [Phase 0 audit](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md), and [arrival-window definitions](PostgreSQL_Arrival_Window_KPIs.md).

## Method and denominators

| Reporting view | Grain and interpretation |
|---|---|
| `route_performance_comparison` | One row per timing cohort and grouping level. Changed and unchanged address sequences have separate total routes, eligible routes, late routes, eligible deliveries, and late deliveries. It includes overall, country, route-size band, and country-by-size results. Null country or band means that dimension is pooled. Unverified routes retain separate counts. |
| `route_performance_standardization_strata` | One country and size stratum per full or retained cohort, with both groups' counts, support status, and common weight. |
| `route_performance_standardized` | One weighted comparison per full or retained cohort, including support coverage and changed-minus-unchanged gaps. |
| `visit_displacement_lateness` | One row per timing cohort, displacement band, address status, and visit-order status. Shows all visit occurrences, distinct represented routes, eligible deliveries, late deliveries, and the late-delivery proportion. Represented routes can recur across bands. |

Route rates divide routes with at least one eligible late visit by routes with at least one eligible delivery. Delivery rates divide late eligible visits by all eligible delivery visits. Percentage-point gaps always subtract unchanged from changed. A zero denominator yields a null rate or gap. Route size counts all recorded visits, including depot and repeat visits. The route view supplies verified route-grain counts. Displacement uses the occurrence lineage and planned index to link each visit once to its arrival status, and the route/import key links to route context.

The `full` cohort retains every route. `span_at_most_1440` drops routes where the maximum minus minimum across recorded arrival and window offsets exceeds 1,440 minutes. `removed_over_1440` exposes the omitted counts. These are analysis cohorts. The original measurements, route order and flags remain available.

Direct standardization uses the **same pooled eligible-route distribution across country × route-size strata** for both address groups and both endpoints. A stratum is supported with at least 50 eligible routes and 100 eligible delivery visits in each group. These are descriptive reporting thresholds chosen for this task. Each supported stratum receives its pooled eligible-route count divided by the total pooled eligible-route count across supported strata. Standardized rates sum the stratum rates times these weights. For the delivery endpoint, this is a visit-based rate within each stratum averaged over a common **route** distribution. Weights and support are recalculated after the timing exclusion. Crude rates retain the observed group mixes and all strata.

Displacement bands are 0, 1, 2–3, 4–6, and 7+ positions. A zero shift describes a visit, including visits on routes whose order changed. Moved visits on routes with unchanged address order remain a separate cohort of visit-order changes among repeated addresses. They are distinct from routes with exact visit order and from moved visits on routes with changed address order.

## Deployment and QA

Run the [version 011 migration](../03_SQL/03_Analysis/011_Route_Performance_Comparisons.sql) and [read-only QA](../05_Quality_Assurance/Tests/Verify_P002_Route_Performance.sql) from a normal Ubuntu WSL terminal after Task 010. Use the existing development role at the interactive password prompt.

```bash
# Run from the repository root.
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/03_Analysis/011_Route_Performance_Comparisons.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Route_Performance.sql
```

QA independently reconstructs address changes, timing flags, and outcome counts from core by cohort and grouping level. It checks standardization weights and weighted numerators, visit preservation, displacement buckets, and reporting grants. The Task 012 handoff confirms that Task 011 deployed on the live PostgreSQL 18.6 cluster and verification exited with status 0. The disposable verification evidence remains below. Reproduce the standalone database test with the verified local extract:

```bash
python3 -B 05_Quality_Assurance/Tests/dry_run_route_performance.py \
  02_Data_Processed/task008_routes_staging.csv
```

## Verified results

Disposable PostgreSQL 18.6 accepted the migration twice. The full-workbook SQL QA passed, and the reporting role queried all four views. The comparison reconciled 19,647 routes and the displacement view reconciled 249,231 visits. The two sensitivity partitions add back to the full baseline.

| Timing cohort | Routes | Eligible routes | Late routes | Eligible deliveries | Late deliveries |
|---|---:|---:|---:|---:|---:|
| Full | 19,647 | 19,383 | 8,387 | 213,122 | 23,718 |
| Retained at ≤1,440 minutes | 18,479 | 18,238 | 7,771 | 201,796 | 21,748 |
| Removed above 1,440 minutes | 1,168 | 1,145 | 616 | 11,326 | 1,970 |

### Full cohort

Total routes are shown as changed / unchanged. The route and delivery columns show late / eligible for each address group. Gaps are percentage points.

| Country / size | Routes | Changed route | Unchanged route | Route gap | Changed delivery | Unchanged delivery | Delivery gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| All countries / all sizes | 14,378 / 5,269 | 6,525/14,264 (45.74%) | 1,862/5,119 (36.37%) | +9.37 | 18,393/176,423 (10.43%) | 5,325/36,699 (14.51%) | -4.08 |
| Norway / all sizes | 4,603 / 3,835 | 2,357/4,492 (52.47%) | 1,284/3,698 (34.72%) | +17.75 | 6,570/48,590 (13.52%) | 3,481/23,642 (14.72%) | -1.20 |
| Denmark / all sizes | 9,775 / 1,434 | 4,168/9,772 (42.65%) | 578/1,421 (40.68%) | +1.98 | 11,823/127,833 (9.25%) | 1,844/13,057 (14.12%) | -4.87 |
| All countries / 1–5 | 455 / 1,387 | 109/420 (25.95%) | 285/1,283 (22.21%) | +3.74 | 173/1,282 (13.49%) | 557/3,459 (16.10%) | -2.61 |
| All countries / 6–10 | 3,382 / 2,371 | 953/3,317 (28.73%) | 796/2,326 (34.22%) | -5.49 | 2,010/22,690 (8.86%) | 2,040/14,068 (14.50%) | -5.64 |
| All countries / 11–20 | 8,833 / 1,453 | 4,380/8,819 (49.67%) | 735/1,452 (50.62%) | -0.95 | 12,179/117,306 (10.38%) | 2,492/18,012 (13.84%) | -3.45 |
| All countries / 21+ | 1,708 / 58 | 1,083/1,708 (63.41%) | 46/58 (79.31%) | -15.90 | 4,031/35,145 (11.47%) | 236/1,160 (20.34%) | -8.88 |
| Norway / 1–5 | 276 / 1,157 | 72/244 (29.51%) | 224/1,066 (21.01%) | +8.50 | 129/710 (18.17%) | 465/2,890 (16.09%) | +2.08 |
| Norway / 6–10 | 1,448 / 1,849 | 607/1,383 (43.89%) | 637/1,804 (35.31%) | +8.58 | 1,379/9,029 (15.27%) | 1,622/10,648 (15.23%) | +0.04 |
| Norway / 11–20 | 2,630 / 802 | 1,492/2,616 (57.03%) | 403/801 (50.31%) | +6.72 | 4,413/33,724 (13.09%) | 1,316/9,562 (13.76%) | -0.68 |
| Norway / 21+ | 249 / 27 | 186/249 (74.70%) | 20/27 (74.07%) | +0.62 | 649/5,127 (12.66%) | 78/542 (14.39%) | -1.73 |
| Denmark / 1–5 | 179 / 230 | 37/176 (21.02%) | 61/217 (28.11%) | -7.09 | 44/572 (7.69%) | 92/569 (16.17%) | -8.48 |
| Denmark / 6–10 | 1,934 / 522 | 346/1,934 (17.89%) | 159/522 (30.46%) | -12.57 | 631/13,661 (4.62%) | 418/3,420 (12.22%) | -7.60 |
| Denmark / 11–20 | 6,203 / 651 | 2,888/6,203 (46.56%) | 332/651 (51.00%) | -4.44 | 7,766/83,582 (9.29%) | 1,176/8,450 (13.92%) | -4.63 |
| Denmark / 21+ | 1,459 / 31 | 897/1,459 (61.48%) | 26/31 (83.87%) | -22.39 | 3,382/30,018 (11.27%) | 158/618 (25.57%) | -14.30 |

### Retained cohort

Total routes are shown as changed / unchanged. The route and delivery columns show late / eligible for each address group. Gaps are percentage points.

| Country / size | Routes | Changed route | Unchanged route | Route gap | Changed delivery | Unchanged delivery | Delivery gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| All countries / all sizes | 13,531 / 4,948 | 6,077/13,419 (45.29%) | 1,694/4,819 (35.15%) | +10.13 | 16,948/166,628 (10.17%) | 4,800/35,168 (13.65%) | -3.48 |
| Norway / all sizes | 4,284 / 3,594 | 2,124/4,175 (50.87%) | 1,154/3,470 (33.26%) | +17.62 | 5,875/45,244 (12.99%) | 3,145/22,627 (13.90%) | -0.91 |
| Denmark / all sizes | 9,247 / 1,354 | 3,953/9,244 (42.76%) | 540/1,349 (40.03%) | +2.73 | 11,073/121,384 (9.12%) | 1,655/12,541 (13.20%) | -4.07 |
| All countries / 1–5 | 416 / 1,215 | 88/382 (23.04%) | 199/1,129 (17.63%) | +5.41 | 134/1,198 (11.19%) | 381/3,097 (12.30%) | -1.12 |
| All countries / 6–10 | 3,198 / 2,281 | 877/3,133 (27.99%) | 754/2,239 (33.68%) | -5.68 | 1,809/21,626 (8.36%) | 1,898/13,611 (13.94%) | -5.58 |
| All countries / 11–20 | 8,329 / 1,399 | 4,126/8,316 (49.62%) | 699/1,398 (50.00%) | -0.38 | 11,416/111,151 (10.27%) | 2,330/17,390 (13.40%) | -3.13 |
| All countries / 21+ | 1,588 / 53 | 986/1,588 (62.09%) | 42/53 (79.25%) | -17.15 | 3,589/32,653 (10.99%) | 191/1,070 (17.85%) | -6.86 |
| Norway / 1–5 | 244 / 1,012 | 55/213 (25.82%) | 152/931 (16.33%) | +9.50 | 96/643 (14.93%) | 308/2,566 (12.00%) | +2.93 |
| Norway / 6–10 | 1,374 / 1,790 | 556/1,309 (42.48%) | 604/1,748 (34.55%) | +7.92 | 1,228/8,618 (14.25%) | 1,512/10,363 (14.59%) | -0.34 |
| Norway / 11–20 | 2,446 / 767 | 1,354/2,433 (55.65%) | 379/766 (49.48%) | +6.17 | 3,996/31,417 (12.72%) | 1,250/9,187 (13.61%) | -0.89 |
| Norway / 21+ | 220 / 25 | 159/220 (72.27%) | 19/25 (76.00%) | -3.73 | 555/4,566 (12.16%) | 75/511 (14.68%) | -2.52 |
| Denmark / 1–5 | 172 / 203 | 33/169 (19.53%) | 47/198 (23.74%) | -4.21 | 38/555 (6.85%) | 73/531 (13.75%) | -6.90 |
| Denmark / 6–10 | 1,824 / 491 | 321/1,824 (17.60%) | 150/491 (30.55%) | -12.95 | 581/13,008 (4.47%) | 386/3,248 (11.88%) | -7.42 |
| Denmark / 11–20 | 5,883 / 632 | 2,772/5,883 (47.12%) | 320/632 (50.63%) | -3.51 | 7,420/79,734 (9.31%) | 1,080/8,203 (13.17%) | -3.86 |
| Denmark / 21+ | 1,368 / 28 | 827/1,368 (60.45%) | 23/28 (82.14%) | -21.69 | 3,034/28,087 (10.80%) | 116/559 (20.75%) | -9.95 |

### Size composition and common weights

The full-cohort composition below uses eligible routes because those routes form the late-route denominator. Each percentage is the band’s share of its address group.

| Visits per route | Changed eligible routes | Unchanged eligible routes |
|---|---:|---:|
| 1–5 | 420 (2.94%) | 1,283 (25.06%) |
| 6–10 | 3,317 (23.25%) | 2,326 (45.44%) |
| 11–20 | 8,819 (61.83%) | 1,452 (28.36%) |
| 21+ | 1,708 (11.97%) | 58 (1.13%) |

| Timing cohort | Comparison | Changed routes | Unchanged routes | Route gap | Changed deliveries | Unchanged deliveries | Delivery gap |
|---|---|---:|---:|---:|---:|---:|---:|
| Full | Crude | 45.74% | 36.37% | +9.37 | 10.43% | 14.51% | -4.08 |
| Full | Crude on supported strata | 43.34% | 35.88% | +7.46 | 10.17% | 14.32% | -4.15 |
| Full | Standardized | 42.27% | 42.42% | -0.15 | 11.08% | 14.10% | -3.02 |
| Retained | Crude | 45.29% | 35.15% | +10.13 | 10.17% | 13.65% | -3.48 |
| Retained | Crude on supported strata | 43.03% | 34.66% | +8.37 | 9.97% | 13.52% | -3.55 |
| Retained | Standardized | 41.71% | 41.69% | +0.02 | 10.53% | 13.27% | -2.73 |

| Timing cohort | Supported strata | Pooled eligible routes retained for weighting |
|---|---:|---:|
| Full | 6/8 | 17,617/19,383 |
| Retained | 6/8 | 16,597/18,238 |

Sparse strata receive no standardization weight. Counts below are changed / unchanged.

| Timing cohort | Country / size | Eligible routes | Eligible deliveries |
|---|---|---:|---:|
| Full | Norway / 21+ | 249 / 27 | 5,127 / 542 |
| Full | Denmark / 21+ | 1,459 / 31 | 30,018 / 618 |
| Retained | Norway / 21+ | 220 / 25 | 4,566 / 511 |
| Retained | Denmark / 21+ | 1,368 / 28 | 28,087 / 559 |

### Visit displacement

Counts show the full cohort and the timing-retained cohort. Each cell gives late deliveries / eligible deliveries. The view also provides total visits and represented-route counts for each cell.

| Address order | Visit order | Positions moved | Full | Retained |
|---|---|---:|---:|---:|
| Unchanged | Exact | 0 | 4,493/30,241 (14.86%) | 4,039/29,006 (13.92%) |
| Unchanged | Changed | 0 | 625/4,994 (12.52%) | 570/4,770 (11.95%) |
| Unchanged | Changed | 1 | 171/1,259 (13.58%) | 160/1,204 (13.29%) |
| Unchanged | Changed | 2–3 | 28/179 (15.64%) | 24/165 (14.55%) |
| Unchanged | Changed | 4–6 | 6/18 (33.33%) | 5/16 (31.25%) |
| Unchanged | Changed | 7+ | 2/8 (25.00%) | 2/7 (28.57%) |
| Changed | Changed | 0 | 5,854/59,957 (9.76%) | 5,412/57,250 (9.45%) |
| Changed | Changed | 1 | 4,556/45,067 (10.11%) | 4,230/42,712 (9.90%) |
| Changed | Changed | 2–3 | 3,922/38,458 (10.20%) | 3,640/36,262 (10.04%) |
| Changed | Changed | 4–6 | 2,217/20,677 (10.72%) | 2,043/19,167 (10.66%) |
| Changed | Changed | 7+ | 1,844/12,264 (15.04%) | 1,623/11,237 (14.44%) |

## Interpretation and limits

Among eligible routes, 73.8% of the changed group had 11 or more visits, compared with 29.5% of the unchanged group. The all-address late-route rate also rose with size, from 23.14% in the 1–5 band to 63.93% in the 21+ band. The changed group had a lower late-route rate in three of the four pooled size bands. Restricting the crude comparison to supported strata still gave a +7.46 pp route gap. Giving the groups the same country/size weights reduced that gap to −0.15 pp. With long timing spans excluded, the standardized route gap was +0.02 pp. The contrast between crude and standardized results demonstrates the effect of the group composition on these descriptive comparisons.

The standardized delivery-level gap remained negative in both timing cohorts. Within changed-address routes, late-delivery rates rose from 9.76% for unmoved visits to 15.04% for visits displaced by seven or more positions. The corresponding retained-cohort rates were 9.45% and 14.44%. The most displaced repeated-address cohorts were small, including only 8 eligible deliveries at seven or more positions in the full cohort.

The route endpoint is sensitive to the number of opportunities to encounter a late stop. Size bands leave variation within each band, and the comparisons do not account for window width, route complexity, or other dispatch conditions. Visits on the same route are related observations. The 24-hour cutoff also removes potentially valid long routes. Standardized rates describe only the supported strata and do not estimate a causal effect.

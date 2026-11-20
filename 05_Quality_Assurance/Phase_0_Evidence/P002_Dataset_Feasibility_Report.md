# P002 Dataset Feasibility Report

**Decision: GO for a SQL-based dispatch exception case study.** The workbook supports paired stop-level sequence analysis, observed delivery arrival exceptions, and planned versus actual straight-line route comparisons.

**Recommended business problem.** Help dispatch managers identify routes with late delivery arrivals and distinguish sequence changes that warrant review from routine resequencing. Prioritize reviews by country, route profile, and adequately sized driver cohorts.

## Source and provenance

| Item | Finding |
|---|---|
| Dataset | Last-mile delivery route deviations dataset: planned vs. actual routes |
| Publisher and version | Mendeley Data, version 1, published 13 December 2024 |
| Authors | Anna Konovalenko, Lars Magnus Hvattum, Kim Aleksander Hammer Iversen |
| DOI and source | [10.17632/kkwgfvmtxn.1](https://doi.org/10.17632/kkwgfvmtxn.1) · [Official version page](https://data.mendeley.com/datasets/kkwgfvmtxn/1) |
| Dataset license | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit the authors, link the source and license, and indicate transformations when sharing derived material. |
| Workbook | `routes_performance.xlsx`, inspected in place in Windows Downloads through WSL. The personal account path is omitted. |
| Size and audit date | 19,713,337 bytes. User reported downloading from the official repository before the 2026-11-19 audit. Local file modification time was 2026-11-19 12:32:58 CST. |
| SHA-256 | `8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00` |

## Workbook counts and schema

`Sheet1` is the sole worksheet. Its dimensions are `A1:P249232`, with one header row and **249,231 visit records**. The sheet contains **19,647 distinct Route IDs**, independently confirmed by reading the worksheet XML. This matches the published file-based reanalysis and exceeds the data descriptor's 19,497 route pairs by 150. Use 19,647 as the unfiltered workbook count. The publications do not establish what produced the lower count. [Data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC13122835/) · [File-based analysis, §2.1](https://www.mdpi.com/2571-5577/9/11/219#sec2dot1-asi-09-00219)

Each row represents one visit occurrence with its planned and actual positions. The table preserves the workbook's column order and groups adjacent fields with compatible types.

| Workbook columns | Observed Excel / Python types | Candidate PostgreSQL representation |
|---|---|---|
| Route ID, Driver ID, Stop ID, Address ID, Week ID, Country | Numeric / int | Integer identifiers and numeric country code |
| Day of Week | Text / str | Text with weekday validation |
| IndexP, IndexA | Numeric / int | Integer, zero-based position |
| Arrived Time, Earliest Time, Latest Time | Numeric / int and float | Numeric relative minutes |
| DistanceP, DistanceA | Numeric / int and float | Numeric Haversine kilometers |
| Depot, Delivery | Numeric / int | Boolean after validating 0 and 1 |

## Data quality and SQL grain

- The workbook has **400 raw Driver IDs**, **13,125 raw Stop IDs**, and **10,864 raw Address IDs**. One driver code and eight codes each for stops and addresses appear in both countries. Country-qualified counts are 401 driver keys (189 Norway, 212 Denmark), 13,133 stop-code keys and 10,872 address keys. These are reporting identities. The data cannot establish whether a shared code represents the same entity.
- Route IDs span 0–19,646 with no gaps. Each route has exactly one country and driver. Both sequence columns are permutations of 0 through the number of visits minus one on every route. Use `route(route_id)` as the parent and `visit(route_id, index_p)` as the child, with a unique constraint on `(route_id, index_a)`. Carry both indices on the visit row and use `LAG` independently in each sequence to recover predecessors.
- Stop IDs repeat within 6,622 routes, addresses within 10,961, and depot Stop IDs within 6,064. Across the file, 308 raw Stop IDs map to more than one Address ID. Retain every visit occurrence and avoid a join that assumes uniqueness of a stop or address within a route. Use country-qualified address and driver dimensions if needed. Keep Week ID and weekday at visit grain. There are 32 week codes (0–31), 2,567 routes span weekday labels, and 567 span week codes.
- All 3,987,696 visit cells are populated. There are zero full-row duplicates, formula or error cells, invalid weekday labels, out-of-domain country or flag values, negative or nonfinite numeric values, reversed window bounds, and invalid route permutations. There are 27 zero-width windows and 4,884 records flagged as both depot and delivery. The latter are excluded from customer delivery KPIs. The time columns contain both integer and fractional numeric values. The respective fractional-type counts for arrival, earliest, and latest are 248,695, 1,752, and 1,624.
- The first leg is zero for each order on every route. There are 15,996 planned and 15,502 actual zero-length legs between consecutive visits with the same address. One actual leg between the same address code has a nonzero distance (0.0566 km, route 7545, actual index 17). Preserve the source value and flag it for review.
- The minimum offset is zero on every route. Actual indices contain 4,643 adjacent arrival ties and 2,180 adjacent arrival reversals across 1,513 routes with a reversal. The largest reversal is 57,552.85 minutes on route 18768. Use `IndexA` for the workbook’s recorded sequence and show the timing anomalies separately. Sorting by arrival would silently change the observed ordering.

## Planned versus actual sequence

Visit match requires `IndexP = IndexA` on every row. Stop-code match compares the ordered Stop ID lists, and address match compares the ordered Address ID lists. Lists retain repeats and include depot visits. In this file, stop-code and visit match counts coincide.

| Scope | Routes | Visits | Median visits per route | Exact visit match | Exact address match |
|---|---:|---:|---:|---:|---:|
| All | 19,647 | 249,231 | 12 | 4,580 (23.31%) | 5,269 (26.82%) |
| Norway (0) | 8,438 | 87,728 | 10 | 3,391 (40.19%) | 3,835 (45.45%) |
| Denmark (1) | 11,209 | 161,503 | 14 | 1,189 (10.61%) | 1,434 (12.79%) |

**15,067 (76.69%) of routes changed visit order.** On 689 routes the address sequence still matched. Overall, 124,310 visits changed position (49.88%). On changed routes the median share of moved visits was 60.00% (90th percentile 86.67%). Moved visits shifted a median of 2 places (90th percentile 7, maximum 27). The workbook-derived 5,269 address matches reproduce the published address-sequence count. [File-based analysis, §2.1](https://www.mdpi.com/2571-5577/9/11/219#sec2dot1-asi-09-00219)

## Delivery-window performance

The denominator is non-depot delivery visits (`Depot = 0 AND Delivery = 1`) with finite, nonnegative times and ordered window bounds. All 213,122 such visits pass those structural checks. Early means arrival < earliest allowable service time. The in-window measure includes both endpoints. Late means arrival > latest allowed arrival. An early driver can wait until service is allowed. These records contain no service-start or completion timestamps.

| Scope | Eligible visits | Early | In window | Late | Routes with a late arrival / eligible routes |
|---|---:|---:|---:|---:|---:|
| All | 213,122 | 24,252 (11.38%) | 165,152 (77.49%) | 23,718 (11.13%) | 8,387 / 19,383 (43.27%) |
| Norway (0) | 72,232 | 5,953 (8.24%) | 56,228 (77.84%) | 10,051 (13.91%) | 3,641 / 8,190 (44.46%) |
| Denmark (1) | 140,890 | 18,299 (12.99%) | 108,924 (77.31%) | 13,667 (9.70%) | 4,746 / 11,193 (42.40%) |

Among early visits, the median gap before service was allowed was **26.28 minutes** (90th percentile 97.78). Among late visits, median lateness was **47.94 minutes** (90th percentile 206.09). These are raw measurements. The largest recorded lateness was 12,814,081.85 minutes on route 11150, and 620 late and 155 early delivery differences exceeded 24 hours. The raw averages are heavily influenced by implausible values.

The table below tests sensitivity by limiting routes to a span of at most 24 hours across all recorded arrival and window offsets. Each route starts at offset zero by construction. This is an audit cutoff and can exclude legitimate longer routes. It preserves the raw results above and leaves ample exceptions for analysis.

| Scope | Routes above cutoff | Retained delivery visits | Late visits | Late routes / retained eligible routes | Late minutes p50 / p90 / p99 |
|---|---:|---:|---:|---:|---:|
| All | 1,168 | 201,796 | 21,748 (10.78%) | 7,771 / 18,238 (42.61%) | 44.93 / 178.69 / 386.31 |
| Norway (0) | 560 | 67,871 | 9,020 (13.29%) | 3,278 / 7,645 (42.88%) | 63.36 / 196.08 / 411.50 |
| Denmark (1) | 608 | 133,925 | 12,728 (9.50%) | 4,493 / 10,593 (42.41%) | 35.10 / 143.67 / 365.61 |

Of routes with eligible deliveries, **6,525 of 14,264 (45.74%)** with a changed address sequence had a late arrival, compared with **1,862 of 5,119 (36.37%)** with matching address sequences. Sequence change and late arrival are separate operational flags. Longer routes have more chances for at least one late stop, and route mix or unobserved conditions may influence both outcomes. Of 401 country-qualified drivers, 370 appear on a route with a late delivery. For the 263 with at least 20 eligible routes, the raw driver-level late-route rate has a median of 47.62% and a 90th percentile of 77.00%.

## Planned versus actual geodesic distance

Sum `DistanceP` and `DistanceA` by route, including reported depot legs. The signed difference is actual minus planned in Haversine kilometers. Treat absolute differences of at most 1e-9 km as equal to account for floating-point rounding.

| Scope | Median planned / actual km | Difference km p05 / p50 / p95 | Mean difference km | Shorter / equal / longer |
|---|---:|---:|---:|---:|
| All | 50.08 / 49.03 | -17.77 / 0.00 / 11.60 | -0.96 | 7,386 / 5,291 / 6,970 |
| Norway (0) | 65.52 / 64.29 | -20.88 / 0.00 / 12.11 | -0.81 | 2,612 / 3,849 / 1,977 |
| Denmark (1) | 40.34 / 39.75 | -16.34 / 0.00 / 11.43 | -1.08 | 4,774 / 1,442 / 4,993 |

Relative difference for 19,646 routes with positive planned totals had a median of 0.00% and a mean of −0.12%. One zero-planned route was excluded from percentages. The signed route differences range from −507.11 to +1,898.70 km. Flag extreme values for review and report quantiles rather than interpreting the mean as a cost effect.

## Dashboard scope and audit reproducibility

Lead with late-arrival rate and the number of routes with late arrivals. Show the eligible denominator, early arrivals, and timing-quality flags alongside them. Pair these KPIs with visit-order and address-order adherence and the distribution of geodesic distance differences. Compare country and route-size bands, and show volume when using country-qualified driver cohorts.

The companion [audit_workbook.py](audit_workbook.py) reads the original in read-only mode and prints its checksum, counts, QA checks, and metric distributions. The original audit used Linux Python 3.14.4 and openpyxl 3.1.5 with et_xmlfile made available from an existing Windows Anaconda installation. To reproduce from the repository root with the official workbook in the ignored raw-data folder, use an isolated environment:

```bash
python3 -m venv .venv-phase0
.venv-phase0/bin/python -m pip install openpyxl==3.1.5
.venv-phase0/bin/python -B 05_Quality_Assurance/Phase_0_Evidence/audit_workbook.py \
  01_Data_Raw/routes_performance.xlsx
```

## Limits and implementation feasibility

- Haversine leg sums describe straight-line route geometry. Road mileage, travel time, fuel use and savings require other data. Anonymous address IDs provide no usable map coordinates.
- Arrival and window values share a route-relative origin. Within-route time differences are meaningful. The dataset does not provide calendar timestamps, time of day, planned arrival times, or verified service completion times. Early arrival can result in waiting and does not establish a service breach.
- One operator in two countries supplies observational data. Route mix, window tightness, or unmeasured conditions can explain apparent driver or country differences. Use comparisons for review prioritization and avoid causal claims or driver rankings from small samples. Stop-level arrival compliance is distinct from package-level fulfillment, failed deliveries, and customer outcomes.
- The inspected portfolio was in a Windows clients folder accessed through WSL. The personal path is omitted. P001 uses a project prefix, numbered folders, explicit QA and a Power BI deliverable. This audit uses a single P002-prefixed folder under the writable Linux home because the Windows portfolio path is outside the writable workspace.
- The Linux environment reports ARM64 (`aarch64`), 8 logical CPUs, 7.5 GiB RAM and Python 3.14.4. PostgreSQL commands were absent from the active Linux path. Python QA ran with openpyxl 3.1.5 sourced from the existing Windows Anaconda installation. PostgreSQL is a practical target at the published scale using typed bulk imports, indexes on the route and sequence keys, SQL window functions and route-level dashboard aggregates. The audit used openpyxl read-only iteration and kept visit tuples in memory for grouping and duplicate checks. A browser-based dashboard backed by aggregate tables or extracts is practical on ARM64. Native Power BI availability, Python package compatibility and load/query performance were not tested.

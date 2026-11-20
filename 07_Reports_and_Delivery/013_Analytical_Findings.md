# Last-mile dispatch exception analysis

## Business problem and evidence

The simulated dispatch team needs to prioritize route exceptions across Norway and Denmark. This analysis measures how often deliveries arrive outside their windows, how often visit order changes, and which patterns survive comparisons across similar route sizes and countries.

The workbook contains 249,231 visit records on 19,647 routes. SQL preserves repeated locations and depot visits, pairs each recorded planned and actual position, and links arrival outcomes to the route before comparing groups. The denominator for delivery rates is eligible non-depot delivery visits. The denominator for the late-route rate is routes with at least one such visit. All figures below describe observed associations. [Dataset provenance](../08_Documentation/Dataset_Provenance.md) · [Technical QA](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

## Verified observations

| Arrival outcome | Count / denominator | Rate |
|---|---:|---:|
| Early | 24,252 / 213,122 | 11.38% |
| In window | 165,152 / 213,122 | 77.49% |
| Late | 23,718 / 213,122 | 11.13% |
| Route with any eligible late arrival | 8,387 / 19,383 | 43.27% |

Among late deliveries, median lateness was **47.94 minutes** and P90 was **206.09 minutes**. Early arrival records time before the window opens and can reflect waiting until service is allowed. [Arrival definitions and QA](../08_Documentation/PostgreSQL_Arrival_Window_KPIs.md)

**Resequencing was common.** Visit order changed on 15,067 of 19,647 routes (76.69%), and 124,310 of 249,231 visits moved (49.88%). On 689 routes, visit order changed while the complete address order remained unchanged. Dispatch review should distinguish these cases from changes in the order of locations. [Route sequence QA](../08_Documentation/PostgreSQL_Route_Sequence_Analytics.md)

**The late-route association depended on route composition.** Changed address order accounted for 6,525 late routes among 14,264 eligible routes (45.74%), compared with 1,862 of 5,119 (36.37%) for unchanged order. About 73.8% of eligible changed-address routes had 11 or more visits, compared with 29.5% of unchanged-address routes. The changed group had a lower late-route rate in three of the four pooled size bands. The +9.37 percentage-point crude gap was +7.46 points on supported strata before weighting and −0.15 after applying the same country and size weights to both groups. The two excluded 21+ strata had fewer than 50 eligible unchanged-address routes each. [Cohort tables and methods](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

The crude **late-delivery** rate was 10.43% for changed address order and 14.51% for unchanged order. The standardized delivery rates were 11.08% and 14.10%. These use delivery-based rates within strata averaged over a common eligible-route distribution. A larger route has more opportunities to record a late arrival, so route and delivery rates answer different questions. [Standardization definitions](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

**Timing sensitivity reduced lateness severity and left the standardized route gap near zero.** Excluding routes whose timing spans exceeded 1,440 minutes removed 1,168 routes, 11,326 eligible deliveries and 1,970 late deliveries. The retained late-delivery rate was 21,748 of 201,796 (10.78%). The retained late-route rate was 7,771 of 18,238 (42.61%). The standardized changed-minus-unchanged gaps were +0.02 points for routes and −2.73 for deliveries. [Timing sensitivity results](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

**The typical route had no paired geodesic distance change.** The median signed difference was 0.00 km, with P05 −17.77 km and P95 +11.60 km. The shorter and longer groups had similar late-route rates (45.73% and 45.75%). Equal-distance routes had a lower late-route rate (36.42%) and higher late-delivery rate (14.52%). These pooled comparisons reflect distinct route and delivery denominators. Distance flags identified 98 routes for review. [Distance comparisons and flags](../08_Documentation/PostgreSQL_Route_Distance_Analytics.md)

## Data quality and uncertainty

The consolidated check matched every staged row to a typed visit and route, including all 16 source fields. Recorded timings include ties, reversals and extreme spans. The 4,884 depot rows also marked as deliveries remain in the records and are ineligible for delivery KPIs. Equal-address consecutive legs can legitimately be zero. One nonzero actual leg on consecutive records with the same address code was retained for review. [Phase 0 evidence](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md)

The workbook represents one operator and records route-relative minutes. Calendar timestamps, service completion, traffic, stop delays, and dispatch reasons are unavailable. Visits within a route are related observations. Broad size bands leave differences within cohorts. The 24-hour screen can omit legitimate long routes. Geodesic sums describe straight-line route geometry. Road travel, fuel use and costs require additional operational measurements.

## Operational implications and investigation

1. **Triage genuine arrival exceptions.** Review high-lateness visits within country and route size, with timing anomaly flags visible. Pilot this as a dispatch workflow and measure whether it helps identify actionable exceptions.
2. **Investigate timing and visit-order records.** Ask the data owner whether long offsets and reversals reflect overnight operations, clock alignment, or recording issues. Those explanations are hypotheses. A log of actual service-start times and exception reasons would help distinguish them.
3. **Investigate displacement within comparable routes.** On changed-address routes, the observed late-delivery rate was 9.76% at zero displacement and 15.04% at seven or more positions. Compare routes with similar delivery volume, window widths, and operating conditions before using displacement to prioritize interventions. Severe displacement among unchanged-address routes has very small samples. [Displacement cohort sizes](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)
4. **Validate distance flags with route telemetry.** Ask the data owner to check the 98 flagged routes, especially extreme paired gaps and the same-address anomaly. Collect road-network or vehicle telemetry before evaluating mileage or cost.

# Last-mile delivery intelligence

**Final draft for review · Simulated dispatch consulting engagement · 20 November 2026**

## Decision for dispatch

Prioritize severe late arrivals within comparable route sizes and countries. Use address-order changes and timing flags to guide case review. The pooled late-route gap between changed and unchanged address order nearly disappears when both groups are weighted to the same distribution of country and route-size bands.

## Business problem and scope

The simulated dispatch team needs a repeatable way to find arrival exceptions, distinguish meaningful address-order changes from swaps among repeated visits, and review unusual recorded distances. This engagement analyzed the versioned workbook from one operator in Norway and Denmark. It covers 249,231 visit records on 19,647 routes. PostgreSQL reconciled all 16 source fields and retained each visit occurrence, including depots and repeated addresses. The dashboard supports descriptive review at delivery and route levels. [Charter](../00_Admin_and_Scope/Project_Charter.md) · [Technical QA](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

## Verified findings

| Arrival KPI | Count / denominator | Rate |
|---|---:|---:|
| Early arrivals | 24,252 / 213,122 eligible delivery visits | 11.38% |
| In-window arrivals | 165,152 / 213,122 eligible delivery visits | 77.49% |
| Late arrivals | 23,718 / 213,122 eligible delivery visits | 11.13% |
| Routes with an eligible late arrival | 8,387 / 19,383 routes with eligible deliveries | 43.27% |

Eligible deliveries are non-depot delivery visits with valid timing. Both arrival-window endpoints count as in window. Among the 23,718 late arrivals, the median was **47.94 minutes** and P90 was **206.09 minutes** past the latest allowed arrival. Early arrivals may reflect waiting. The workbook does not record when service began or ended. [Arrival-window definitions](../08_Documentation/PostgreSQL_Arrival_Window_KPIs.md)

**Visit-order changes were common.** Visit order changed on 15,067 of 19,647 routes (76.69%). Address order changed on 14,378 (73.18%). On 689 routes, visits moved while the recorded address sequence stayed the same. The visit-level and address-level measures therefore support different dispatch questions. [Route sequence evidence](../08_Documentation/PostgreSQL_Route_Sequence_Analytics.md)

### Route composition and standardization

| Endpoint | Crude changed | Crude unchanged | Crude gap | Standardized changed | Standardized unchanged | Standardized gap |
|---|---:|---:|---:|---:|---:|---:|
| Routes with a late arrival | 45.74% | 36.37% | +9.37 pp | 42.27% | 42.42% | −0.15 pp |
| Late delivery visits | 10.43% | 14.51% | −4.08 pp | 11.08% | 14.10% | −3.02 pp |

The crude late-route counts were 6,525 of 14,264 eligible changed-address routes and 1,862 of 5,119 unchanged-address routes. Routes of 11 or more visits made up 73.8% of the eligible changed-address group and 29.5% of the unchanged group. Larger routes have more opportunities to record at least one late arrival. Changed-address routes had lower late-route rates in three of the four pooled size bands.

Standardization used common country × route-size weights over six supported strata covering **17,617 of 19,383 eligible routes** (90.89%). Both groups needed at least 50 eligible routes and 100 eligible visits in each stratum. The two 21+ visit strata stayed in the crude rates and were excluded from weighting because their unchanged-order groups were sparse. The standardized delivery rate averages within-stratum delivery rates using the common **route** distribution. Gaps are changed minus unchanged in percentage points. They describe the observed sample under these weights. [Cohorts and weights](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

### Timing sensitivity and anomalies

The full cohort retains all timing spans. Applying the exploratory ≤1,440-minute screen removed 1,168 routes, 11,326 eligible deliveries and 1,970 late deliveries. The retained cohort had **21,748 late deliveries out of 201,796 (10.78%)** and **7,771 late routes out of 18,238 eligible routes (42.61%)**. The retained late-arrival median was 44.93 minutes and P90 was 178.69 minutes. The standardized route gap was +0.02 pp and the delivery gap was −2.73 pp. The screen can also remove legitimate long routes.

The source recorded 4,643 adjacent arrival ties and 2,180 adjacent reversals in actual visit order. It also recorded 27 zero-width windows and 4,884 depot visits marked as deliveries. Depot rows remain traceable and are excluded from the eligible delivery denominator. [Phase 0 evidence](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md) · [Sensitivity QA](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

### Geodesic distance and review flags

| Recorded route category | Routes | Late routes / eligible routes | Late deliveries / eligible deliveries |
|---|---:|---:|---:|
| Shorter | 7,386 | 3,350 / 7,325 (45.73%) | 9,032 / 89,937 (10.04%) |
| Equal | 5,291 | 1,872 / 5,140 (36.42%) | 5,343 / 36,793 (14.52%) |
| Longer | 6,970 | 3,165 / 6,918 (45.75%) | 9,343 / 86,392 (10.81%) |

Median paired change was **0.00 geodesic km**, with P05 −17.77 and P95 +11.60 km. The shorter and longer groups had similar late-route rates. Equal-distance routes had the lowest late-route rate and the highest late-delivery rate. The rates have different denominators and reflect the composition of the groups.

The distance screen flagged **98 routes**. Of these, 96 had absolute gaps of at least 100 geodesic km. One route had zero planned distance, leaving its percentage change unavailable. Route 7545 had a recorded nonzero actual leg between consecutive visits with the same address code. Flags are review prompts and the measurements are retained. [Distance definitions and QA](../08_Documentation/PostgreSQL_Route_Distance_Analytics.md)

## Hypotheses to investigate

- Timing reversals and unusually long spans could reflect overnight work, inconsistent clock alignment, or data entry. The workbook cannot distinguish these explanations.
- Within changed-address routes, late-delivery rates were 9.76% for unmoved visits and 15.04% for visits moved seven or more positions. Task mix, delivery-window widths and operating conditions could contribute to the difference. The comparison alone gives no estimate of the effect of moving a stop. [Displacement results](../08_Documentation/PostgreSQL_Route_Performance_Comparisons.md)

## Recommended dispatch actions

| Priority | Action | Evidence to collect |
|---|---|---|
| 1 | Pilot an exception review by country and route size. Start with severe late arrivals and review flagged timing separately. | Log the reason, whether the exception was actionable, and whether the review led to a follow-up. |
| 2 | Validate the timing rules with the data owner. Sample reversals, long spans and zero-width windows against source operations. | Capture timestamp conventions, service-start times and dispatch exception reasons. |
| 3 | Review flagged distances with route telemetry before using distance in routing or cost decisions. | Collect odometer, GPS or road-network distance data and verify the same-address anomaly. |
| 4 | Compare like-for-like cohorts before changing dispatch policy. | Add delivery volume, window width, route complexity and operating-condition data. Document any proposed intervention and its evaluation separately. |

## Limitations

One operator and one workbook limit generalization. Visits on a route are related. Country and broad size bands leave variation within strata, and sparse strata limit standardized coverage. Arrival offsets are route-relative. Calendar timestamps, service completion, traffic and intervention data are unavailable. The distance totals are straight-line Haversine leg sums. Road mileage, fuel, travel time and costs require separate measurements.

## Source and attribution

Anna Konovalenko, Lars Magnus Hvattum, and Kim Aleksander Hammer Iversen (2024), *Last-mile delivery route deviations dataset: planned vs. actual routes*, Mendeley Data v1, DOI 10.17632/kkwgfvmtxn.1, CC BY 4.0. The project extracted workbook values, assigned SQL types, derived visit and route metrics, and aggregated and filtered reporting cohorts. [Dataset](https://data.mendeley.com/datasets/kkwgfvmtxn/1) · [DOI](https://doi.org/10.17632/kkwgfvmtxn.1) · [License](https://creativecommons.org/licenses/by/4.0/) · [Provenance](../08_Documentation/Dataset_Provenance.md)

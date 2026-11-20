# P002 project charter

**Status:** Phase 1 scope for review.

## Simulated client and business problem

A fictional last-mile dispatch team operating across Norway and Denmark needs to prioritize route exceptions for review. Dispatchers need to know which routes had late arrivals, where visit order changed, and whether changes coincided with differences in straight-line route length. The engagement uses public operational data. The dispatch team is a fictional audience for the case study.

## Objectives and analytical questions

- Quantify delivery arrival performance. Where are late arrivals most frequent or severe, and how sensitive are results to unusual timing offsets?
- Measure adherence to the planned itinerary. How often do visits move, and how often does the address sequence itself change?
- Compare planned and actual geodesic route totals. How are signed differences distributed by country and route size?
- Examine where sequence changes and lateness co-occur. Do descriptive patterns persist across comparable route-size bands? Use country-qualified driver cohorts only where counts support comparison.

## Proposed deliverables

- PostgreSQL schema, repeatable workbook-to-database load, and SQL views at visit and route grain.
- Reconciliation and QA evidence for source integrity, keys, KPI denominators, and timing sensitivity.
- A dispatch dashboard with headline KPIs, country and route-size breakdowns, and route-level exception detail.
- A client findings brief, metric definitions, and a portfolio write-up with source attribution.

## Initial KPI definitions

| KPI | Rule and denominator |
|---|---|
| Eligible delivery coverage | Non-depot delivery visits with finite, nonnegative arrival and window offsets and earliest ≤ latest, divided by all non-depot delivery visits. |
| Early, in-window, and late arrival rates | Use eligible delivery visits as the denominator. Early is arrival < earliest, in-window includes both endpoints, and late is arrival > latest. |
| Lateness severity | Median and 90th percentile of arrival minus latest, among eligible late visits. Report the sample size. |
| Routes with a late arrival | Routes with at least one eligible late visit divided by routes with at least one eligible delivery visit. |
| Exact visit and address adherence | For routes with valid paired sequences, count exact visit-order matches and exact ordered address-list matches separately. Preserve repeated visits and depot positions. |
| Visit displacement | Moved visits divided by visits on valid paired routes. Report absolute position changes among moved visits. |
| Geodesic route variance | Sum actual leg km minus sum planned leg km by route with complete valid leg data, including recorded depot legs. Relative change uses only routes with positive planned totals. Report counts and quantiles across eligible routes. |

Show raw timing metrics alongside a sensitivity view for routes whose recorded time offsets span at most 24 hours. Treat this cutoff as an exploratory QA choice. An early arrival records time before allowable service and can reflect waiting.

## Data limitations and QA risks

Phase 0 verified 249,231 visits and 19,647 routes. Repeated Stop IDs, addresses, and depot visits require visit-level keys. Country-qualified IDs are reporting keys because some codes recur across countries. Preserve `IndexA` despite arrival ties and reversals. Flag extreme timing offsets, zero-width windows, depot rows marked as deliveries, and anomalous leg values. Preserve source values and document any analysis exclusions and their denominators.

Distance is straight-line Haversine kilometers. Timing fields are minutes relative to a route origin and do not provide calendar timestamps or service completion. Route mix and unobserved operating conditions limit comparisons across drivers and countries.

## Success criteria and scope exclusions

- Reconcile source checksum, row and route totals, and key integrity with Phase 0. Retain repeated visits and explain any differences in eligible subsets.
- Demonstrate that KPI outputs can be reproduced from the versioned workbook. Show denominators, timing sensitivities, and aggregate-to-detail reconciliation.
- Deliver a reviewable dashboard and findings brief that distinguish late arrival from resequencing and present comparisons as descriptive evidence.
- The engagement scope excludes route optimization, predictive dispatch, road mileage and cost estimation, package or completion metrics, causal evaluation, and individual driver performance scoring.

# Dashboard user guide

**Final draft for review · Simulated dispatch engagement**

The dashboard is a local review tool for the workbook v1 snapshot. Once the operator has started Streamlit, open `http://127.0.0.1:8501` in the Windows browser. Use the sidebar to switch pages. [Launch instructions](020_Delivery_and_Acceptance.md)

## Choose the timing scope

- **Full workbook** includes all routes and is the starting point for baseline KPIs.
- **Timing span ≤1,440 minutes** excludes entire routes whose recorded arrival and window offsets span more than 24 hours. It is a sensitivity check. Some long routes may be legitimate.
- The timing selection persists across pages. Check the selected scope before recording a number. Country, size and table filters belong to their individual pages or panels.

## Executive Overview

Read the card denominator beneath each percentage. Compare the delivery and route late rates, then use median and P90 to understand severity among late deliveries. The outcome bar shows early, in-window and late visits. Use the adjacent chart to compare crude and standardized late-route rates by address order. The support line shows how many country/size strata and eligible routes the weighted comparison covers. Expand **Delivery-level comparison** for the visit-based endpoint and **Definitions and limitations** for interpretation. The timing readout shows the number of long-span routes and visits included or excluded under the current timing choice.

## Route Performance & Exceptions

1. Set **Country** and **Route size** to compare changed and unchanged address order in matching cohorts. Use the counts shown with each rate to assess sample size.
2. In **Displacement and late deliveries**, choose the address and visit-order states separately. The panel uses all countries and sizes. A route can contribute visits to more than one displacement band.
3. Use **Search by route ID** for an exact numeric ID or apply **Table address order** and **Exception filter**. The table shows up to 25 routes per page. **Previous** and **Next** move through results. Changing the scope returns to the first page.
4. Choose **Select a route to inspect**. Open **Selected route sequence detail** for the moved-visit count. The visit table contains planned and actual positions, stop and address IDs, outcome and timing flags. Expand **Visit timing, eligibility and source detail** for arrival and window offsets, exclusions and worksheet rows. Actual position links the tables. More visits, if present, appear on additional visit pages.

## Distance Deviations & Data Quality

1. Set **Country**, **Route size**, and **Address order**. Review shorter, equal and longer counts, then compare late-route and late-delivery rates separately.
2. Use P05, median and P95 to read the distribution of paired actual-minus-planned geodesic distance. The zero marker is the reference. The percentiles apply to the selected cohort.
3. Use **Distance category**, **Review flags** and **Search by route ID** for the table. These controls apply to the table and selected route. Choose **All routes** to find a route without a review flag.
4. Choose **Inspect a route** and open **Route distance and flag detail**. The panel shows planned and actual geodesic kilometers, signed and absolute change, percentage change and review reasons. Try route **7545** with Full timing and the **Distance review** filter to see the nonzero actual same-address leg.

## Reading results

| Term | Meaning |
|---|---|
| Eligible delivery | A non-depot delivery visit with valid recorded timing. Early arrival may reflect waiting. |
| Late-route rate | Routes with at least one eligible late arrival divided by routes with at least one eligible delivery. |
| Late-delivery rate | Late eligible deliveries divided by all eligible deliveries in the selected scope. |
| Changed address order | The complete recorded order of address codes changed. Visit-order swaps at one location can leave address order unchanged. |
| Standardized rate | The groups are weighted to a common country and route-size distribution across supported strata. The adjustment is descriptive. |
| Signed distance change | Actual minus planned straight-line Haversine kilometers. A zero planned total has no percentage change. |
| Unavailable | The measure lacks eligible observations, a valid denominator, or the needed data. |

When no rows match, broaden the table filters or check the timing cohort. If reporting data is unavailable, confirm the local server and reporting login using the handoff instructions. Share the page name, selected filters and route ID with the operator so the issue can be reproduced. [Delivery and verification](020_Delivery_and_Acceptance.md) · [Dataset and license](../08_Documentation/Dataset_Provenance.md)

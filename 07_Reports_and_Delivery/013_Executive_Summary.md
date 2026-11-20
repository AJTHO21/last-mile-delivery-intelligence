# Executive summary | Last-mile dispatch exceptions

**Draft for the simulated dispatch client**

Prioritize reviews by lateness severity and route size. Changes in address order can help identify routes to investigate, especially when paired with a late arrival or an unusual recorded distance.

- **11.13% of eligible deliveries arrived late** (23,718 of 213,122). Among late arrivals, the median was 47.94 minutes and the 90th percentile was 206.09 minutes past the window close. **43.27% of eligible routes** had at least one late arrival (8,387 of 19,383).
- **The pooled gap shrank after weighting for country and route size.** The share of routes with late arrivals was 45.74% for changed address order and 36.37% for unchanged order. Applying common country and size weights across six supported strata yielded 42.27% and 42.42%, respectively. After excluding unusually long timing spans, the standardized gap was +0.02 percentage points.
- **The typical paired change in recorded distance was zero.** There were 7,386 shorter routes, 5,291 equal, and 6,970 longer. Distances are straight-line Haversine leg sums. Road mileage, driving time and costs require separate measurements.

Start with a dispatch review of severe late arrivals within comparable route sizes and countries. Review unusually long timing spans separately with the data owner, and collect service-start times and exception reasons before evaluating operational changes.

Analysis covers a public workbook from one operator in Norway and Denmark. Results are descriptive and use route-relative arrival times. [Analytical findings](013_Analytical_Findings.md) · [Dataset provenance](../08_Documentation/Dataset_Provenance.md)

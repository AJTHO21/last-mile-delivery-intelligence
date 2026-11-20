# Executive dashboard architecture

**Task 014 · Design and data contract**

Help dispatch leaders find late-arrival exceptions worth reviewing, understand how the pooled comparison changes across comparable routes, and triage timing and distance quality flags. The three pages follow the validated Task 013 findings. [Charter](../00_Admin_and_Scope/Project_Charter.md) · [Findings](../07_Reports_and_Delivery/013_Analytical_Findings.md) · [Executive summary](../07_Reports_and_Delivery/013_Executive_Summary.md) · [Technical QA](../05_Quality_Assurance/013_Consolidated_Technical_QA.md)

## Platform decision

| Option | Fit on this laptop | Validation before implementation |
|---|---|---|
| **Recommended: Streamlit in Ubuntu WSL, rendered in the Windows browser** | Keeps Python and PostgreSQL in the same WSL environment. The server reads PostgreSQL with the existing reporting role. The Windows browser renders the dashboard over localhost. Supports parameterized filters, route drill-through, and deliberate separation of crude and standardized results. | In the build phase, create an isolated environment with a supported Python version and confirm ARM64 wheels for the pinned Streamlit and PostgreSQL driver stack. Smoke-test the Windows-to-WSL localhost browser route and PostgreSQL authentication. |
| Power BI Desktop on Windows ARM64 | Microsoft lists Windows on ARM support with the September 2025 cumulative update KB5065789. Desktop includes a PostgreSQL connector with Import and DirectQuery modes. Import is the practical fallback for this fixed workbook snapshot and avoids a database round trip for every interaction. Keep approved views as source datasets. | Check the laptop's Windows build and update status, install or open Desktop, and test a small PostgreSQL import through Windows localhost with the reporting role. Check connector authentication and TLS behavior before designing the model. Actual Windows connector compatibility and refresh were not tested in this phase. |

The recommended layout is **Windows browser → loopback Streamlit in WSL → loopback PostgreSQL as `p002_report`**. Use server-side parameter binding, bounded result sets, and caching keyed by workbook version and selected filters. Bind to localhost and keep secrets in user-private environment configuration. No public hosting, cloud service, or gateway is needed for the local design. If Power BI is required for handoff, keep the same contract and separate the overview and fixed standardization snapshots from the route/visit model. [Streamlit installation](https://docs.streamlit.io/get-started/installation) · [Streamlit PostgreSQL support](https://docs.streamlit.io/develop/tutorials/databases/postgresql) · [Power BI Desktop requirements](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop) · [Power Query PostgreSQL connector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)

## Page design

| Page | Visuals and decisions |
|---|---|
| **Executive Overview** | Four cards for late eligible deliveries, routes with a late arrival, median lateness with P90, and changed address order. Show numerators and denominators. A 100% stacked bar shows early, in-window and late counts. A paired plot compares crude and standardized late-route rates by address status, with supported-strata coverage and a secondary delivery-rate comparison. A sensitivity note gives omitted count and denominator changes. |
| **Route Performance & Exceptions** | Compare changed and unchanged address groups by country and size using paired horizontal bars or dots. Show eligible and late counts in the tooltip and below each cohort. A displacement panel uses bands 0, 1, 2–3, 4–6 and 7+ with address and visit-order context. A route exception table shows route ID, country, size, address/visit match, moved visits, late/eligible deliveries, and flags. Select a row to inspect visit positions, timing offsets and windows, early or late minutes, and flags. |
| **Distance Deviations & Data Quality** | Category bars for shorter, equal and longer, with late-route and late-delivery rates in separate panels. A signed-difference quantile plot shows P05, median and P95 around zero. A quality table shows timing and distance review flags, including zero planned totals and same-address legs. Route selection shows planned, actual, signed, absolute and relative distance with geodesic units. |

### Controls and interactions

- The shared control is **Timing cohort** with Full as the default and Timing span ≤1,440 minutes as the alternative. Show the removed partition as an audit readout. The three partition labels are never summed.
- Pages 2 and 3 allow one country and one size selection, each defaulting to All. The cohort comparison keeps both address groups visible. Use address status, route ID, and exception filters for the route list. On Page 3, distance category and distance-review filters constrain the list and route drill only.
- The displacement panel uses supported aggregate controls for timing, address order, and visit order. Country and size filters apply to the route comparison and route list. Label the displacement panel “All countries and route sizes” so its scope is explicit.
- The standardized card uses the validated country/size population for the selected timing cohort. It has no country or size controls and is computed by SQL. Show six of eight supported strata and the covered eligible-route count. If a comparison group lacks eligible observations, use an unavailable state with its zero denominator.
- KPI cards and exceptions use numerator/denominator tooltips and accessible text, with “Full workbook” or the current timing cohort in the section heading. Display the dataset version. The workbook supplies week codes and relative minutes, so the design has no calendar trend or timestamp control.

### Visual system

Use deep slate `#182431` for headings and navigation, muted slate blue `#58758C` for comparison series, burnt orange `#B34F2B` for true arrival exceptions and quality flags, and pale slate `#EDF2F6` for card backgrounds. Text labels, marker shapes, active-filter state, and patterned fills make color redundant. Keep ordinary changed address order neutral. Desktop wireframes prioritize one main story per page and support narrower cards stacking above charts. [Wireframes](014_Dashboard_Wireframes.md)

## Build-phase handoff

1. Verify the WSL reporting role, runtime dependencies, and browser localhost connection.
2. Deploy and verify the versioned SQL contract from normal WSL.
3. Implement the overview first, then route comparison and drill-through, then distance and quality panels. Verify displayed numerators, denominators, selected scope, and keyboard navigation before sharing a local preview.

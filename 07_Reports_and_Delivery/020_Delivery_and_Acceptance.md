# Delivery handoff and acceptance

**Final acceptance record · Simulated engagement · 20 November 2026**

| Deliverable | Review focus |
|---|---|
| [Client findings report](020_Client_Findings_Report.md) | Approve the decision framing, verified observations and proposed dispatch reviews. |
| [Executive summary](020_Executive_Summary.md) | Approve the headline figures and wording for the simulated audience. |
| [Dashboard user guide](020_Dashboard_User_Guide.md) | Walk through timing selection, bounded route review and detail on each page. |
| [Delivery handoff](020_Delivery_and_Acceptance.md) | Confirm reproducibility, local access and remaining acceptance items. |

## Environment and launch

The reference environment is Windows ARM64 with a browser, Ubuntu WSL2 ARM64, PostgreSQL 18.6 and Python 3.14.4 in the project `.venv`. Direct requirements are Streamlit 1.67.0 and Psycopg 3.3.9. Psycopg uses installed ARM64 libpq. The local host exposes Streamlit only at `127.0.0.1:8501` and PostgreSQL at `127.0.0.1:5432`. The app uses `p002_report` and the private passfile at `~/.config/p002/pgpass`. [Pinned requirements](../06_Dashboard/requirements-smoke.txt) · [Environment and passfile setup](../06_Dashboard/015_Streamlit_Smoke_Runbook.md)

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run dashboard.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --theme.base light --theme.primaryColor '#58758C' --theme.textColor '#182431'
```

Open `http://127.0.0.1:8501` in the Windows browser. Use Ctrl+C to stop the local server.

## Reproduce and verify

1. Obtain workbook v1 from Mendeley Data. The [provenance record](../08_Documentation/Dataset_Provenance.md) identifies the exact SHA-256, worksheet, size and row count.
2. For an empty authorized environment, use the existing runbooks in order. Provision the database and roles (006), apply the schema (007), and extract, checksum and load the workbook (008). On an existing environment, start with verification against the approved snapshot. [Provisioning](../08_Documentation/PostgreSQL_Database_Provisioning.md) · [Schema](../08_Documentation/PostgreSQL_Relational_Schema.md) · [Ingestion](../08_Documentation/PostgreSQL_Ingestion_Runbook.md)
3. Apply reporting migrations in order (009 arrival, 010 sequence, 011 performance, 012 distance), then the dashboard data contract (014). Task 013 is consolidated read-only QA. Follow the linked runbooks for the approved execution order and role. [SQL implementation index](../08_Documentation/PostgreSQL_Implementation_Plan.md) · [Dashboard contract](../06_Dashboard/014_Dashboard_Data_Contract.md)
4. Run the exact commands in the [analytical QA report](../05_Quality_Assurance/013_Consolidated_Technical_QA.md) and the [integrated dashboard QA runbook](../06_Dashboard/019_Integrated_Dashboard_QA.md) from normal WSL. The latter enables all four application live checks and confirms the reporting role, read-only transaction, and absence of staging/core schema access.

## QA evidence and acceptance criteria

| Area | Accept when | Evidence status |
|---|---|---|
| Source and model | Both hashes match, one import holds 249,231 visits on 19,647 routes, and all source fields reconcile to the typed records. | Verified on the approved snapshot. Task 008 live reconciliation was reported as passed. |
| Analytical controls | The consolidated QA success marker appears, all 14 controls match, and standardization uses the documented six supported strata. | Task 013 passed on disposable PostgreSQL 18.6 and on the live WSL PostgreSQL instance. |
| Dashboard contract | Full, retained and removed cohorts reconcile. Grouped results and route drill preserve grain. Reporting-only reads succeed. | Task 014 disposable QA passed. Live deployment and contract QA were reported as passed. |
| Dashboard regression | UI and data tests pass. Timing persists across pages, controls reset pagination, and drill-through displays the correct row and denominator. | All 30 automated tests passed on 20 November 2026, including all four live PostgreSQL checks. |
| Local browser walkthrough | All three dashboard pages open and support their reviewed workflows in the Windows browser. | Visual inspection completed on all three pages, including route 7545 drill-through and distance anomaly review. |
| Keyboard accessibility and narrow-window layout | Controls and details remain usable by keyboard, and labels and tables remain readable at narrow widths. | Pending. |

## Completed visual inspections

- **Executive Overview:** Reviewed the KPI cards, arrival-window chart, and crude and standardized comparisons in the Windows browser.
- **Route Performance & Exceptions:** Inspected the route review and completed visit drill-through for route 7545.
- **Distance Deviations & Data Quality:** Inspected the distance views and reviewed the recorded nonzero actual same-address leg flagged for route 7545.

The walkthrough verifies the reviewed browser workflows. Keyboard accessibility and narrow-window behavior remain open.

## Task 020 internal validation

The original workbook and existing staging extract matched their approved SHA-256 checksums. The four delivery documents passed local link checks. Seventeen displayed rates were recomputed from their reported numerators and denominators, and the arrival, distance and sensitivity partitions reconciled. No discrepancy against the approved headline figures surfaced. Streamlit and Psycopg imported at the pinned versions under ARM64 Python 3.14.4, and pip reported no broken dependencies.

## Open items and documentation gaps

- The published descriptor lists 19,497 route pairs, while the verified workbook has 19,647 routes. The 150-route difference is unresolved. Reports use the audited workbook count. [Phase 0 discrepancy](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md)
- Keyboard accessibility and narrow-window testing remain outstanding. Record those results separately from the completed visual inspections.
- The Task 015 setup runbook records dependency installation as pending in its original sandbox session. Task 020 verified the dependencies are now installed in the project environment. The historical runbook remains the setup reference.
- The project pins direct Python dependencies. It does not currently include a complete transitive lockfile or a separate distributable environment bundle. Record the resolved package list during acceptance if exact environment replay is required.
- The charter also references a portfolio write-up and country-qualified driver cohorts where supported. This handoff is for the simulated client and contains no driver comparisons or publishing package.

## Attribution and analytical limits

Credit Anna Konovalenko, Lars Magnus Hvattum, and Kim Aleksander Hammer Iversen (2024) for *Last-mile delivery route deviations dataset: planned vs. actual routes*, Mendeley Data v1, published 13 December 2024, DOI 10.17632/kkwgfvmtxn.1. Use the CC BY 4.0 attribution, retain source notices, identify changes, and avoid implying author endorsement. This project extracts and types workbook values and applies route aggregation, eligibility rules, and cohort filters and weights. [Official dataset](https://data.mendeley.com/datasets/kkwgfvmtxn/1) · [DOI](https://doi.org/10.17632/kkwgfvmtxn.1) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

Results describe observed arrivals and route composition for one operator. Standardization covers supported strata. Timing is route-relative, and flagged rows remain traceable. Geodesic sums describe straight-line geometry. Road mileage, driving time, costs and causal effects require other evidence. [Client findings and limits](020_Client_Findings_Report.md)

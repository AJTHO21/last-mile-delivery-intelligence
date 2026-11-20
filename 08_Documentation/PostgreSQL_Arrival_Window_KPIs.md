# Arrival-window KPI engineering

**Phase 4, Task 009 · PostgreSQL 18.6**

The [ingestion runbook](PostgreSQL_Ingestion_Runbook.md) records the Task 008 live import and independent reconciliation supplied in the handoff.

## Reporting views

The [version 009 SQL migration](../03_SQL/03_Analysis/009_Arrival_Window_Views.sql) creates or replaces two reporting views in one transaction. The migration grants `p002_report` SELECT on these views. The reporting role has no access to the underlying staging or core schemas.

- `reporting.visit_arrival_window` starts at the source visit grain. A left join on import, worksheet, and row number links to the unique core visit. Its route join uses route and import IDs. Repeated stop and address IDs retain their individual visit rows.
- `reporting.arrival_window_summary` returns one overall row. It counts each arrival class, divides each count by eligible delivery visits, and computes continuous median and 90th percentile lateness among late visits. Rates are proportions. Rates and percentiles are null for an empty eligible denominator. Percentiles are also null when there are no late visits.

Eligibility reasons are evaluated in order.

| Reason | Rule |
|---|---|
| `missing_core_visit` | The source lineage key has no linked typed visit. |
| `depot` | The typed visit is at a depot, including rows also marked delivery. |
| `non_delivery` | The typed visit has no delivery flag. |
| `missing_timing` | An arrival or window offset is null. |
| `invalid_timing` | An offset is negative or nonfinite, or the window is inverted. |
| `eligible_delivery` | A non-depot delivery visit with valid arrival and window offsets. |

The typed schema already enforces timing completeness and validity. The defensive reasons document what the view would do if a future schema permitted those cases. Excluded visits have null arrival status and duration. For eligible visits, arrival before earliest is early, arrival after latest is late, and both window boundaries are included in `in_window`. Early duration is earliest minus arrival. Late duration is arrival minus latest. Durations are populated only for their applicable class.

Timing flags identify adjacent ties and reversals in recorded actual sequence, zero-width windows, depot/delivery overlap, route timing spans above 1,440 minutes, and eligible early or late gaps above 1,440 minutes. The route span is the maximum minus minimum of all arrival and window offsets on the route. These flags preserve source measurements and do not filter the KPI denominator. For the charter's exploratory 24-hour sensitivity cohort, use the visit view with `eligible_delivery AND NOT route_timing_span_over_1440` and recompute denominators within that cohort.

The source describes arrival offsets in minutes. It provides no service-start or completion timestamps. Early arrival can reflect waiting until service is allowed. Lateness measures an arrival deadline exception, and comparisons cannot establish its cause.

## QA and deployment

Run the [read-only verification SQL](../05_Quality_Assurance/Tests/Verify_P002_Arrival_Window.sql) after deploying the views. It checks source coverage and unique lineage, classifications and duration, anomaly counts, denominators, percentiles, and reporting grants.

From the normal Ubuntu WSL terminal:

```bash
# Run from the repository root.
psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
  -f 03_SQL/03_Analysis/009_Arrival_Window_Views.sql \
  -f 05_Quality_Assurance/Tests/Verify_P002_Arrival_Window.sql
```

Use the existing login password at the prompt. The Task 010 handoff confirms that Task 009 live deployment and read-only QA passed in the normal WSL terminal. The migration changes reporting views and grants only. The verification transaction is read-only.

Reproduce the disposable test with the verified Task 008 CSV:

```bash
python3 -B 05_Quality_Assurance/Tests/dry_run_arrival_window.py \
  02_Data_Processed/task008_routes_staging.csv
```

The [synthetic SQL fixture](../05_Quality_Assurance/Tests/Test_Arrival_Window_Fixture.sql) runs only in the disposable database and rolls back its rows. It tests both inclusive boundaries, a zero-width boundary, missing core lineage, depot and non-delivery exclusions, ties and reversals, an extreme late value, and null rates for an empty cohort.

## Observed test results

Both the synthetic fixture and the full-workbook QA passed on disposable PostgreSQL 18.6. Running the migration twice succeeded. The reporting role independently queried the summary and returned 23,718 late visits. The detail view returned 249,231 unique lineage rows, including 36,109 ineligible visits.

| Metric | Count | Share of eligible visits |
|---|---:|---:|
| Eligible delivery visits | 213,122 | 100.00% |
| Early | 24,252 | 11.38% |
| In window | 165,152 | 77.49% |
| Late | 23,718 | 11.13% |

Median lateness among late visits was **47.94 minutes** and P90 was **206.09 minutes**. The QA also reproduced 4,643 adjacent ties, 2,180 adjacent reversals, 27 zero-width windows, 4,884 depot/delivery overlaps, 155 early gaps and 620 late gaps above 24 hours, and 1,168 routes with timing spans above 24 hours.

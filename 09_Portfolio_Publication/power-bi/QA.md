# Power BI analytical QA

The Power BI companion was checked against the approved P002 reporting outputs. Route and delivery outcomes use different eligible denominators. The timing cohorts overlap. Check each cohort separately.

| Check | Full workbook | Timing span ≤ 1,440 minutes |
|---|---:|---:|
| Late deliveries / eligible deliveries | 23,718 / 213,122 | 21,748 / 201,796 |
| Late routes / eligible routes | 8,387 / 19,383 | 7,771 / 18,238 |
| Median / P90 lateness among late eligible visits | 47.94 / 206.09 min | 44.93 / 178.69 min |
| Crude changed-minus-unchanged late-route gap | +9.37 pp | +10.13 pp |
| Standardized changed-minus-unchanged late-route gap | −0.15 pp | +0.02 pp |
| Total routes | 19,647 | 18,479 |
| Shorter / equal / longer | 7,386 / 5,291 / 6,970 | 7,030 / 4,967 / 6,482 |
| Distance-review routes | 98 | 69 |
| P05 / median / P95 actual-minus-planned distance | −17.77 / 0.00 / +11.60 km | −17.48 / 0.00 / +10.26 km |

Offline QA reconciled the 16 country-and-size comparison rows, 22 displacement cells, and all 90 distance scopes. Exact scope filters select one published rollup before reading a percentile. The report preserves single-direction cohort filtering and keeps aggregate charts independent of bounded review tables. Schema and field-reference checks covered the available Microsoft schemas. Inherited definitions whose schema was unavailable were checked against reviewed baseline hashes. Guarded synchronization and rollback were tested on a disposable copy.

The showcase image records the Power BI Desktop Executive Overview. The repository’s separate Streamlit screenshots document the reference dashboard. This package provides analytical and offline technical evidence. It does not include a downloadable PBIP. A clean-machine Power BI open and refresh and a complete Desktop acceptance run for a portable build remain unverified.

[Original P002 QA](../../05_Quality_Assurance/013_Consolidated_Technical_QA.md) · [Dashboard acceptance evidence](../../07_Reports_and_Delivery/020_Delivery_and_Acceptance.md) · [Distance verification](../../05_Quality_Assurance/Tests/Verify_P002_Route_Distance.sql)

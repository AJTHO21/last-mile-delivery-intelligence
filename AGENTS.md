# P002 workspace instructions

- Consult the charter and dataset provenance before changing scope, metric definitions, or grain.
- Preserve the original workbook, the original Phase 0 evidence and its [in-project copies](05_Quality_Assurance/Phase_0_Evidence/), and P001. Read source data in place or from a verified local copy. Write generated data to `02_Data_Processed/`.
- Use one row per visit occurrence and preserve both source indices. Join visits to routes by Route ID and qualify driver and address reporting keys by country.
- Record KPI eligibility, denominators, and exclusions. Use the recorded actual index for sequence. Flag timing anomalies and document sensitivity rules. Label distance as Haversine kilometers and time as route-relative minutes.
- Keep raw and processed data, credentials, caches, and local environments out of version control. Use synthetic fixtures for tests intended for sharing.
- Keep work within the requested phase. Obtain explicit direction before publishing or pushing. Dataset-derived public materials require the attribution in the provenance document.

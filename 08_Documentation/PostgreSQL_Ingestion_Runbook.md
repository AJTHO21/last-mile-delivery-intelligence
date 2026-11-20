# P002 workbook ingestion

**Phase 3, Task 008 · PostgreSQL 18.6**

The Task 007 handoff confirms that all four tables were deployed and its verification suite passed. Task 008 implemented and dry-ran the load. The Task 009 handoff confirms that the authorized live ingestion and independent reconciliation then passed in the normal WSL terminal. The verified source hash matched the audited workbook. The live results were one import, 249,231 staging records, 19,647 routes, 249,231 core visits, 213,122 eligible visits, and 23,718 late eligible visits. These results were supplied in the handoff.

## Source and validation

[Dataset provenance](Dataset_Provenance.md) identifies the official version and workbook checksum. The [extractor](../04_Python/extract_routes_workbook.py) hashes the bytes it reads and extracts that same byte image with the Python standard library. It reads the verified version's worksheet XML, requires the exact 16 headers and cell types, and writes the cell values with worksheet name and Excel row number. Numeric XML text is preserved verbatim. Python validates using exact decimals and the SQL loader casts to PostgreSQL `numeric` without floating-point intermediates. Output is deterministic UTF-8 CSV. The extractor publishes a complete file only and refuses an existing output path.

The [SQL loader](../03_SQL/02_Load/008_Load_Routes.sql) uses client-side COPY into a temporary table. It checks source-row coverage, route-level country and driver consistency, and both contiguous permutations. Database constraints enforce one visit per source row, the two route sequence keys, and same-import route and source lineage. Reconciliation joins on the constrained keys and compares the stored rows with every expected staging and core row. No visit key or join depends on Stop ID or Address ID.

The load uses one transaction. Table locks serialize publication and protect the comparisons. Any conflicting version metadata or route ID held by another import raises an error. An exact hash rerun compares all existing rows and performs no persistent inserts. A divergent or incomplete same-hash load raises an error and leaves the stored rows for investigation. The loader contains no truncate, delete or update operations.

## Dry-run results

| Reconciliation | Python extraction | Disposable PostgreSQL 18.6 |
|---|---:|---:|
| Source visit rows | 249,231 | 249,231 |
| Routes | 19,647 | 19,647 |
| Core visits | — | 249,231 |
| Eligible delivery visits | 213,122 | 213,122 |
| Late eligible delivery visits | 23,718 | 23,718 |

An eligible visit is a non-depot delivery with valid arrival and window values. All non-depot deliveries passed those checks. Lateness uses arrival strictly greater than the latest offset.

The full extraction retained repeated stop IDs on 6,622 routes and repeated addresses on 10,961. It retained 2,180 adjacent arrival reversals, 4,643 ties, 27 zero-width windows, 4,884 depot rows flagged as deliveries, 1,168 routes whose timing offsets span over 24 hours, and one nonzero actual leg between consecutive visits at the same address code. The load leaves these values intact for downstream QA.

Two extractions produced identical CSV bytes. Four [extractor tests](../05_Quality_Assurance/Tests/test_ingestion_extractor.py) passed. The [database dry run](../05_Quality_Assurance/Tests/dry_run_ingestion.py) tested the full load, a same-hash no-op, rollback on source version and reused route conflicts, rejection of a duplicate actual position, and detection of stored same-hash drift. The disposable instance ran in standalone mode with no listener. It used server-side COPY from the local file to exercise the same staging table and SQL validations. The subsequent live ingestion success is recorded above.

Reproduce the automated tests from the project root once the local CSV exists.

```bash
python3 -B 05_Quality_Assurance/Tests/test_ingestion_extractor.py
python3 -B 05_Quality_Assurance/Tests/dry_run_ingestion.py \
  02_Data_Processed/task008_routes_staging.csv
```

## Live execution in the normal Ubuntu WSL terminal

Use these commands when the live load is authorized. Place the official workbook at `01_Data_Raw/routes_performance.xlsx` before running the commands below. Use the existing verified CSV if available. The conditional extraction supports a fresh workspace while leaving an existing file intact. If the CSV checksum fails, stop and generate a new file at an unused path for review.

```bash
# Run from the repository root.
source_xlsx=01_Data_Raw/routes_performance.xlsx
mkdir -p 02_Data_Processed
staging_csv=02_Data_Processed/task008_routes_staging.csv
if [ ! -e "$staging_csv" ]; then
  python3 -B 04_Python/extract_routes_workbook.py "$source_xlsx" "$staging_csv"
fi
printf '%s  %s\n' \
   8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00 "$source_xlsx" \
   1aa8609bf2539f191d4d43c9be7fbf5ad3926b055239c70fee6eb383e6f20273 "$staging_csv" |
  sha256sum --check --strict &&
  psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile \
    -f 03_SQL/02_Load/008_Load_Routes.sql < "$staging_csv"
```

Use the existing role password at the interactive prompt. Expect `P002 load reconciled` after commit. For any error, inspect the first reported failure before retrying. Keep the generated CSV local.

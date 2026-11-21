# Reproduce the reporting outputs

The published reproduction route is PostgreSQL and the reference Streamlit dashboard. Obtain the versioned workbook separately from Mendeley Data. Use a local PostgreSQL database and configure a private credential for the read-only reporting role. [Dataset and workbook checksum](../../08_Documentation/Dataset_Provenance.md) · [Database provisioning](../../08_Documentation/PostgreSQL_Database_Provisioning.md)

1. From the checkout root, place the downloaded workbook at the relative path described in the ingestion runbook, then extract it with checksum verification.

   ```bash
   mkdir -p 01_Data_Raw 02_Data_Processed
   python3 -B 04_Python/extract_routes_workbook.py \
     01_Data_Raw/routes_performance.xlsx 02_Data_Processed/task008_routes_staging.csv
   ```

2. Follow the schema and ingestion instructions. Apply reporting SQL 009, 010, 011, 012 and 014 in order, using the documented development role. Use the reporting role for dashboard reads. [Ingestion runbook](../../08_Documentation/PostgreSQL_Ingestion_Runbook.md) · [SQL implementation order](../../08_Documentation/PostgreSQL_Implementation_Plan.md)
3. Follow the dependency, credential, and launch steps in the root README. Run the offline suite from the checkout root after the environment is ready.

   ```bash
   .venv/bin/python -B -m unittest discover -s 05_Quality_Assurance/Tests -p 'test_*.py' -v
   ```

4. Use the opt-in live checks after deployment and compare both timing cohorts with the [public QA summary](QA.md). [Live test and dashboard commands](../../06_Dashboard/019_Integrated_Dashboard_QA.md)

## Power BI portability

This package contains documentation and an Executive Overview screenshot. The Power BI PBIP is currently machine-specific and is not included as a downloadable report. It imports private CSV snapshots from fixed Windows paths, and a refresh on another machine requires portable source paths and approved replacement inputs. A cache-free open and refresh on a clean Windows profile remain unverified.

A future portable demo would need a cache-free project, parameterized paths, licensed and approved synthetic or independently regenerated inputs, review of embedded report identifiers and model metadata, and a successful open and refresh on a clean Windows profile. For now, the existing PostgreSQL and Streamlit workflow is the supported reproduction path.

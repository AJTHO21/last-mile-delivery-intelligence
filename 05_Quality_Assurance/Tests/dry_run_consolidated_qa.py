"""Run consolidated analytical SQL checks in standalone PostgreSQL 18."""
import argparse
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from dry_run_ingestion import LOAD, MIGRATION, ROOT, standalone_sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    csv_path = args.csv.resolve(strict=True)
    pgbin = Path("/usr/lib/postgresql/18/bin")
    with TemporaryDirectory(prefix="p002-consolidated-") as scratch:
        data = Path(scratch) / "data"
        subprocess.run([pgbin / "initdb", "-D", data, "--no-sync", "--no-locale",
                        "--auth=peer", "--no-instructions"], check=True, stdout=subprocess.DEVNULL)

        def run(database, statements):
            chunks = ["\n".join(line for line in statement.splitlines() if line.strip())
                      for statement in statements]
            result = subprocess.run([pgbin / "postgres", "--single", "-j", "-D", data, database],
                                    input="\n\n".join(chunks) + "\n\n", text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
                                    env={**os.environ, "LC_ALL": "C"})
            if re.search(r"\b(?:ERROR|FATAL|PANIC):", result.stdout):
                raise RuntimeError(result.stdout)
            return result.stdout

        run("postgres", ["CREATE ROLE p002_dev LOGIN;", "CREATE ROLE p002_report LOGIN;",
                         "CREATE DATABASE p002_last_mile;"])
        report_sql = ROOT / "03_SQL/03_Analysis/009_Arrival_Window_Views.sql"
        sequence_sql = ROOT / "03_SQL/03_Analysis/010_Route_Sequence_Views.sql"
        comparison_sql = ROOT / "03_SQL/03_Analysis/012_Route_Distance_Analytics.sql"
        performance_sql = ROOT / "03_SQL/03_Analysis/011_Route_Performance_Comparisons.sql"
        qa_sql = Path(__file__).with_name("013_Consolidated_Analytical_QA.sql")
        # Resolve the suite's psql includes in order for the standalone backend.
        suite = "\n".join(qa_sql.with_name(line.split()[1]).read_text()
                          if line.startswith(r"\ir ") else line
                          for line in qa_sql.read_text().splitlines())
        run("p002_last_mile", [
            "CREATE SCHEMA staging AUTHORIZATION p002_dev;",
            "CREATE SCHEMA core AUTHORIZATION p002_dev;",
            "CREATE SCHEMA reporting AUTHORIZATION p002_dev;",
            "GRANT USAGE ON SCHEMA reporting TO p002_report;",
            "SET ROLE p002_dev;",
            *standalone_sql(MIGRATION.read_text(), csv_path),
            *standalone_sql(report_sql.read_text(), csv_path),
        ])
        result = run("p002_last_mile", [
            "SET ROLE p002_dev;",
            *standalone_sql(LOAD.read_text(), csv_path),
            *standalone_sql(sequence_sql.read_text(), csv_path),
            *standalone_sql(performance_sql.read_text(), csv_path),
            *standalone_sql(comparison_sql.read_text(), csv_path),
            *standalone_sql(suite, csv_path),
            "SET ROLE p002_report;",
            *[f"SELECT count(*) AS reporting_rows FROM reporting.{name};" for name in (
                "visit_arrival_window", "arrival_window_summary", "visit_sequence_deviation",
                "route_sequence_deviation", "route_sequence_lateness_summary", "route_performance_comparison",
                "route_performance_standardization_strata", "route_performance_standardized",
                "visit_displacement_lateness", "route_distance", "route_distance_comparison",
            )],
        ])
        for line in result.splitlines():
            if 'NOTICE:' in line or re.search(r'\d+: (result|reporting_rows|supported_strata|timing_cohort|\w+_gap_pp) = ', line):
                print(line.strip())


if __name__ == "__main__":
    main()

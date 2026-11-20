"""Exercise Task 008 against disposable PostgreSQL 18 with no server listener."""
import argparse
import csv
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "03_SQL/01_Schema/007_Initial_Relational_Schema.sql"
LOAD = ROOT / "03_SQL/02_Load/008_Load_Routes.sql"


def standalone_sql(script, csv_path):
    # Adapt these versioned psql files to postgres --single -j, which accepts
    # one statement per blank-line-delimited block and has no psql meta commands.
    copy_line = r"\copy pg_temp.incoming FROM PSTDIN WITH (FORMAT csv, HEADER MATCH)"
    csv_literal = "'" + str(csv_path).replace("'", "''") + "'"
    script = script.replace(copy_line,
                            f"RESET ROLE; COPY pg_temp.incoming FROM {csv_literal} WITH (FORMAT csv, HEADER MATCH); SET ROLE p002_dev;")
    script = "\n".join(line for line in script.splitlines()
                       if not line.lstrip().startswith(("--", "\\")))
    pieces = re.split(r"(\$\$.*?\$\$)", script, flags=re.S)
    for index in range(1, len(pieces), 2):
        pieces[index] = pieces[index].replace(";", "\0")
    return [statement.strip().replace("\0", ";") + ";"
            for statement in "".join(pieces).split(";") if statement.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    csv_path = args.csv.resolve(strict=True)
    pgbin = Path("/usr/lib/postgresql/18/bin")
    with TemporaryDirectory(prefix="p002-ingest-") as scratch:
        data = Path(scratch) / "data"
        subprocess.run([pgbin / "initdb", "-D", data, "--no-sync", "--no-locale",
                        "--auth=peer", "--no-instructions"], check=True, stdout=subprocess.DEVNULL)

        def run(database, statements, expected_error=None):
            # Remove internal blank lines before passing statements to -j.
            chunks = ["\n".join(line for line in stmt.splitlines() if line.strip()) for stmt in statements]
            result = subprocess.run([pgbin / "postgres", "--single", "-j", "-D", data, database],
                                    input="\n\n".join(chunks) + "\n\n", text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
                                    env={**os.environ, "LC_ALL": "C"})
            errors = re.findall(r"\b(?:ERROR|FATAL|PANIC):\s+([^\n]+)", result.stdout)
            if expected_error is None and errors or expected_error is not None and (
                len(errors) != 1 or expected_error not in errors[0]
            ):
                raise RuntimeError(result.stdout)
            return result.stdout

        run("postgres", ["CREATE ROLE p002_dev LOGIN;", "CREATE DATABASE p002_last_mile;"])
        run("p002_last_mile", ["CREATE SCHEMA staging AUTHORIZATION p002_dev;",
                             "CREATE SCHEMA core AUTHORIZATION p002_dev;",
                             "SET ROLE p002_dev;", *standalone_sql(MIGRATION.read_text(), csv_path)])
        load = standalone_sql(LOAD.read_text(), csv_path)
        owner = "SET ROLE p002_dev;"
        summary = """SELECT concat_ws('/', (SELECT count(*) FROM staging.source_import),
            (SELECT count(*) FROM staging.source_visit), (SELECT count(*) FROM core.route),
            count(*), count(*) FILTER (WHERE NOT depot AND delivery),
            count(*) FILTER (WHERE NOT depot AND delivery AND arrived_minutes > latest_minutes))
            AS counts FROM core.visit;"""
        # Use a deliberately conflicting synthetic import in the scratch cluster.
        fake_import = """INSERT INTO staging.source_import (import_id, source_filename, source_doi, source_version, sha256)
            OVERRIDING SYSTEM VALUE VALUES (-1, 'fixture.xlsx', 'fixture', 1, repeat('a',64));"""
        run("p002_last_mile", [owner, fake_import,
                              "INSERT INTO core.route VALUES (0, -1, 0, 0);"])
        def reject(message, script=load):
            failing_statement = next(i for i, item in enumerate(script) if message in item)
            run("p002_last_mile", [owner, *script[:failing_statement + 1]], message)

        reject("belongs to another import")
        assert '\"1/0/1/0/0/0\"' in run("p002_last_mile", [owner, summary])
        print("Conflicting route ID rejected and transaction rolled back")
        run("p002_last_mile", [owner, "DELETE FROM core.route WHERE import_id = -1;",
                              """UPDATE staging.source_import SET source_doi = '10.17632/kkwgfvmtxn.2', source_version = 2
                                 WHERE import_id = -1;"""])
        reject("Conflicting source hash or version")
        assert '\"1/0/0/0/0/0\"' in run("p002_last_mile", [owner, summary])
        print("Conflicting version metadata rejected and transaction rolled back")
        run("p002_last_mile", [owner, "DELETE FROM staging.source_import WHERE import_id = -1;"])
        bad_csv = Path(scratch) / "duplicate-actual-index.csv"
        with csv_path.open(newline="", encoding="utf-8") as original, bad_csv.open(
            "w", newline="", encoding="utf-8"
        ) as altered:
            # The first two data rows are on route 0.
            header, first, second = [next(csv.reader([original.readline()])) for _ in range(3)]
            second[header.index("index_a")] = first[header.index("index_a")]
            csv.writer(altered, lineterminator="\n").writerows((header, first, second))
            shutil.copyfileobj(original, altered)
        reject("Route assignment, route count, or permutation mismatch",
               standalone_sql(LOAD.read_text(), bad_csv))
        assert '\"0/0/0/0/0/0\"' in run("p002_last_mile", [owner, summary])
        print("Duplicate actual index rejected and transaction rolled back")
        for label in ("Initial load", "Exact rerun"):
            results = run("p002_last_mile", [owner, *load, summary])
            assert "P002 load reconciled" in results and '\"1/249231/19647/249231/213122/23718\"' in results
            print(f"{label} passed: 1 import / 249231 staging rows / 19647 routes / "
                  "249231 visits / 213122 eligible / 23718 late")
        run("p002_last_mile", [owner, """UPDATE staging.source_visit SET stop_id = '-1'
                 WHERE worksheet_name = 'Sheet1' AND source_row_number = 2;"""])
        reject("Stored rows or operational reconciliation differ")
        assert '\"-1\"' in run("p002_last_mile", [owner,
            "SELECT stop_id FROM staging.source_visit WHERE source_row_number = 2;"])
        print("Divergent same-hash rerun rejected without repairing stored rows")


if __name__ == "__main__":
    main()

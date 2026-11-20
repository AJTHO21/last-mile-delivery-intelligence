"""Extract the audited workbook's exact XML cell values to a staging CSV."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
from hashlib import file_digest, sha256
from io import BytesIO
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

WORKBOOK_SHA256 = "8f17d15e189c99a34f2446daeaaf1a65d1e79045a94c4d3c452391c96d9cee00"
EXPECTED = (249231, 19647, 213122, 23718)
HEADERS = (
    "Route ID", "Driver ID", "Stop ID", "Address ID", "Week ID", "Country",
    "Day of Week", "IndexP", "IndexA", "Arrived Time", "Earliest Time",
    "Latest Time", "DistanceP", "DistanceA", "Depot", "Delivery",
)
CSV_HEADERS = (
    "worksheet_name", "source_row_number", "route_id", "driver_id", "stop_id",
    "address_id", "week_id", "country", "day_of_week", "index_p", "index_a",
    "arrived_time", "earliest_time", "latest_time", "distance_p", "distance_a",
    "depot", "delivery",
)
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WEEKDAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
UNSIGNED = re.compile(r"[0-9]+")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def worksheet_rows(payload):
    # The verified version has a single Sheet1, inline strings, and no formulas.
    with ZipFile(BytesIO(payload)) as workbook, workbook.open("xl/worksheets/sheet1.xml") as sheet:
        grid = None
        count = 0
        for event, node in iterparse(sheet, events=("start", "end")):
            if event == "start" and node.tag == NS + "sheetData":
                grid = node
            if event != "end" or node.tag != NS + "row":
                continue
            count += 1
            if node.get("r") != str(count) or len(node) != len(HEADERS):
                raise ValueError(f"Sheet1 row {count}: missing, extra, or nonsequential cells")
            values = []
            for index, cell in enumerate(node):
                address = f"{chr(65 + index)}{count}"
                is_text = count == 1 or index == 6
                expected_kind = "inlineStr" if is_text else "n"
                child = NS + "is/" + NS + "t" if is_text else NS + "v"
                value = cell.findtext(child)
                if (cell.tag != NS + "c" or cell.get("r") != address
                        or cell.get("t", "n") != expected_kind
                        or cell.find(NS + "f") is not None or not value):
                    raise ValueError(f"Sheet1 {address}: missing value or unexpected cell type")
                values.append(value)
            grid.remove(node)
            if count == 1:
                if tuple(values) != HEADERS:
                    raise ValueError("Sheet1: unexpected column headers")
            else:
                yield count, values


def validate_row(values):
    for index in (0, 1, 2, 3, 4, 7, 8):
        if not UNSIGNED.fullmatch(values[index]) or int(values[index]) > 2147483647:
            raise ValueError(f"{HEADERS[index]} must be a nonnegative PostgreSQL integer")
    if values[6] not in WEEKDAYS:
        raise ValueError("Invalid weekday")
    if any(values[index] not in ("0", "1") for index in (5, 14, 15)):
        raise ValueError("Country, Depot, and Delivery must be 0 or 1")
    numeric = []
    for index in range(9, 14):
        if not NUMBER.fullmatch(values[index]):
            raise ValueError(f"{HEADERS[index]} must be a finite decimal")
        value = Decimal(values[index])
        if value < 0:
            raise ValueError(f"{HEADERS[index]} must be nonnegative")
        numeric.append(value)
    arrival, earliest, latest, planned_km, actual_km = numeric
    if earliest > latest or (int(values[7]) == 0 and planned_km) or (int(values[8]) == 0 and actual_km):
        raise ValueError("Invalid window bounds or nonzero first leg")
    return arrival, earliest, latest, actual_km


def extract(source, output):
    # Read and hash the same bytes used for extraction.
    payload = source.read_bytes()
    if sha256(payload).hexdigest() != WORKBOOK_SHA256:
        raise ValueError("Workbook SHA-256 does not match the audited source")
    routes = {}
    counts = Counter()
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=output.parent,
                                prefix=".routes-", delete=False) as csv_file:
            temporary = Path(csv_file.name)
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(CSV_HEADERS)
            for row_number, values in worksheet_rows(payload):
                try:
                    arrival, earliest, latest, actual_km = validate_row(values)
                    route, driver, stop, address = map(int, values[:4])
                    planned, actual = map(int, values[7:9])
                    assignment = (values[5], driver)
                    route_assignment, planned_positions, actual_visits = routes.setdefault(route, (assignment, set(), {}))
                    if assignment != route_assignment or planned in planned_positions or actual in actual_visits:
                        raise ValueError("Inconsistent route assignment or duplicate sequence position")
                    planned_positions.add(planned)
                    actual_visits[actual] = (arrival, earliest, latest, stop, address, actual_km)
                except ValueError as exc:
                    raise ValueError(f"Sheet1 row {row_number}: {exc}") from exc
                eligible = values[14:] == ["0", "1"]
                counts.update(visits=1, eligible=eligible, late=eligible and arrival > latest,
                              zero_width=earliest == latest, depot_delivery=values[14:] == ["1", "1"])
                writer.writerow(("Sheet1", row_number, *values))
            for route, (_, planned, actual) in routes.items():
                expected = set(range(len(planned)))
                if planned != expected or actual.keys() != expected:
                    raise ValueError(f"Route {route}: incomplete sequence permutation")
                ordered = [actual[i] for i in range(len(actual))]
                counts["repeated_stop_routes"] += len({row[3] for row in ordered}) < len(ordered)
                counts["repeated_address_routes"] += len({row[4] for row in ordered}) < len(ordered)
                counts["arrival_reversals"] += sum(a[0] > b[0] for a, b in zip(ordered, ordered[1:]))
                counts["arrival_ties"] += sum(a[0] == b[0] for a, b in zip(ordered, ordered[1:]))
                counts["same_address_nonzero_actual_legs"] += sum(
                    a[4] == b[4] and b[5] != 0 for a, b in zip(ordered, ordered[1:])
                )
                counts["routes_over_1440_minutes"] += max(max(row[:3]) for row in ordered) > 1440
            counts["routes"] = len(routes)
            baseline = tuple(counts[key] for key in ("visits", "routes", "eligible", "late"))
            if baseline != EXPECTED:
                raise ValueError(f"Reconciliation failed: expected {EXPECTED}, observed {baseline}")
        # Publish only a complete validated file and fail if the destination already exists.
        output.hardlink_to(temporary)
    finally:
        if temporary is not None:
            temporary.unlink()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        counts = extract(args.source, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    with args.output.open("rb") as csv_file:
        print("CSV SHA-256:", file_digest(csv_file, "sha256").hexdigest())
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()

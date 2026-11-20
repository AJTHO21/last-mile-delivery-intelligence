"""Read-only Phase 0 audit. Pass the original workbook path as the sole argument."""
from collections import Counter, defaultdict
from hashlib import file_digest
from math import fsum, isfinite
from pathlib import Path
from statistics import mean, quantiles
import sys

from openpyxl import load_workbook


def distribution(values):
    p = quantiles(values, n=100, method="inclusive")
    return [round(x, 5) for x in (min(values), p[4], p[49], p[89], p[94], p[98], max(values), mean(values))]


def main(path):
    with path.open("rb") as file:
        print("Bytes and SHA-256:", path.stat().st_size, file_digest(file, "sha256").hexdigest())
    workbook = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    print("Sheets:", [(s.title, s.max_row, s.max_column) for s in workbook])
    sheet = workbook["Sheet1"]
    rows = sheet.iter_rows()
    headers = [cell.value for cell in next(rows)]
    print("Header:", headers)
    types = [Counter() for _ in headers]
    routes = defaultdict(list)
    seen = set()
    quality = Counter()
    scopes = {name: defaultdict(set) for name in ("driver", "stop", "address", "stop_address")}
    weekdays = Counter()
    timing_by_type = Counter()
    for cells in rows:
        row = tuple(cell.value for cell in cells)
        for counts, cell in zip(types, cells, strict=True):
            counts[(cell.data_type, type(cell.value).__name__)] += 1
        quality["blank_cells"] += row.count(None)
        quality["duplicates_after_first"] += row in seen
        seen.add(row)
        route, driver, stop, address, week, country, day, p, a, arrival, earliest, latest, dp, da, depot, delivery = row
        routes[route].append(row)
        for name, value in (("driver", driver), ("stop", stop), ("address", address)):
            scopes[name][value].add(country)
        scopes["stop_address"][stop].add(address)
        weekdays[day] += 1
        quality["invalid_codes"] += country not in (0, 1) or depot not in (0, 1) or delivery not in (0, 1)
        quality["invalid_integer_ids_or_indices"] += any(type(x) is not int or x < 0 for x in (route, driver, stop, address, week, p, a))
        quality["invalid_weekday"] += day not in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        quality["invalid_numbers"] += any(not isfinite(x) or x < 0 for x in (arrival, earliest, latest, dp, da))
        quality["inverted_windows"] += earliest > latest
        quality["zero_width_windows"] += earliest == latest
        quality["first_leg_nonzero_planned"] += p == 0 and dp != 0
        quality["first_leg_nonzero_actual"] += a == 0 and da != 0
        quality["depot_flagged_delivery"] += depot == delivery == 1
        timing_by_type[depot, delivery, "early" if arrival < earliest else "late" if arrival > latest else "inside"] += 1
    workbook.close()

    print("Rows, routes:", sum(map(len, routes.values())), len(routes))
    print("Column types:", dict(zip(headers, types, strict=True)))
    print("ID distinct / country-qualified / multi-value IDs:", {
        key: (len(values), sum(map(len, values.values())), sum(len(v) > 1 for v in values.values()))
        for key, values in scopes.items()
    })
    print("Weekdays:", weekdays, "Weeks:", sorted({row[4] for visit_rows in routes.values() for row in visit_rows}))
    print("Stop outcomes by depot and delivery flags:", timing_by_type)
    print("Route ID range:", min(routes), max(routes))
    summaries = defaultdict(Counter)
    samples = defaultdict(lambda: defaultdict(list))
    driver_counts = defaultdict(Counter)
    anomaly_examples = {}
    for route, visits in routes.items():
        planned = sorted(visits, key=lambda row: row[7])
        actual = sorted(visits, key=lambda row: row[8])
        country, driver = planned[0][5], planned[0][1]
        n = len(visits)
        quality["routes_mixed_country"] += len({row[5] for row in visits}) > 1
        quality["routes_mixed_driver"] += len({row[1] for row in visits}) > 1
        quality["routes_multi_weekday"] += len({row[6] for row in visits}) > 1
        quality["routes_multi_week"] += len({row[4] for row in visits}) > 1
        quality["invalid_planned_permutation_routes"] += [r[7] for r in planned] != list(range(n))
        quality["invalid_actual_permutation_routes"] += [r[8] for r in actual] != list(range(n))
        quality["repeated_stop_id_routes"] += len({r[2] for r in visits}) < n
        quality["repeated_address_routes"] += len({r[3] for r in visits}) < n
        quality["repeated_depot_stop_routes"] += len({r[2] for r in visits if r[14]}) < sum(r[14] for r in visits)
        quality["nonzero_route_time_origin"] += min(x for r in visits for x in r[9:12]) != 0
        quality["actual_arrival_tie_pairs"] += sum(x[9] == y[9] for x, y in zip(actual, actual[1:]))
        reversals = [x[9] - y[9] for x, y in zip(actual, actual[1:]) if x[9] > y[9]]
        quality["actual_arrival_reversal_pairs"] += len(reversals)
        quality["routes_with_arrival_reversal"] += bool(reversals)
        if reversals and max(reversals) > anomaly_examples.get("maximum_reversal", (0,))[0]:
            anomaly_examples["maximum_reversal"] = (max(reversals), route)
        for left, right in zip(actual, actual[1:]):
            if left[3] == right[3] and right[13] != 0:
                anomaly_examples["nonzero_same_address_leg"] = (route, right[8], right[3], right[13])
        for seq, col in ((planned, 12), (actual, 13)):
            quality[f"zero_same_address_legs_{col}"] += sum(x[3] == y[3] and y[col] == 0 for x, y in zip(seq, seq[1:]))
            quality[f"nonzero_same_address_legs_{col}"] += sum(x[3] == y[3] and y[col] != 0 for x, y in zip(seq, seq[1:]))
        shifts = [abs(r[7] - r[8]) for r in visits]
        moved = sum(shift > 0 for shift in shifts)
        stop_match = [r[2] for r in planned] == [r[2] for r in actual]
        address_match = [r[3] for r in planned] == [r[3] for r in actual]
        dp = fsum(r[12] for r in visits)
        da = fsum(r[13] for r in visits)
        delta = da - dp
        deliveries = [r for r in visits if r[14] == 0 and r[15] == 1]
        eligible = [r for r in deliveries if all(isfinite(x) and x >= 0 for x in r[9:12]) and r[10] <= r[11]]
        late = [r[9] - r[11] for r in eligible if r[9] > r[11]]
        early = [r[10] - r[9] for r in eligible if r[9] < r[10]]
        # One day is an exploratory sensitivity cutoff for excessive offsets,
        # measured across all arrival and window values within the route.
        span = max(x for r in visits for x in r[9:12])
        ordinary_span = span <= 1440
        if late and max(late) > anomaly_examples.get("maximum_lateness", (0,))[0]:
            worst = max(eligible, key=lambda r: r[9] - r[11])
            anomaly_examples["maximum_lateness"] = (max(late), route, worst[7], worst[9:12])
        driver_counts[country, driver].update(routes=1, changed=bool(moved), delivery_routes=bool(eligible), late_routes=bool(late))
        for group in ("all", country):
            summaries[group].update(
                routes=1, visits=n, occurrence_match=moved == 0, stop_match=stop_match,
                address_match=address_match, moved_visits=moved, unchanged_addresses_changed_visits=address_match and moved > 0,
                delivery_count=len(deliveries), eligible=len(eligible), late=len(late), early=len(early),
                inside=len(eligible) - len(late) - len(early), delivery_routes=bool(eligible), late_routes=bool(late),
                early_routes=bool(early),
                routes_over_1440_min=not ordinary_span,
                late_over_1440_min=sum(x > 1440 for x in late),
                early_over_1440_min=sum(x > 1440 for x in early),
                sensitivity_delivery_routes=bool(eligible) and ordinary_span,
                sensitivity_late_routes=bool(late) and ordinary_span,
                sensitivity_deliveries=len(eligible) if ordinary_span else 0,
                sensitivity_late=len(late) if ordinary_span else 0,
                sensitivity_early=len(early) if ordinary_span else 0,
                equal_distance=abs(delta) <= 1e-9,
                longer=delta > 1e-9, shorter=delta < -1e-9, zero_planned=dp == 0,
            )
            if eligible:
                comparison = "same_address_order" if address_match else "changed_address_order"
                summaries[group][comparison + "_eligible_routes"] += 1
                summaries[group][comparison + "_late_routes"] += bool(late)
                comparison = "same_visit_order" if moved == 0 else "changed_visit_order"
                summaries[group][comparison + "_eligible_routes"] += 1
                summaries[group][comparison + "_late_routes"] += bool(late)
            s = samples[group]
            s["route_size"].append(n)
            s["pct_visits_moved"].append(100 * moved / n)
            s["mean_absolute_shift"].append(sum(shifts) / n)
            if moved:
                s["changed_route_pct_visits_moved"].append(100 * moved / n)
            s["changed_visit_shift"].extend(shift for shift in shifts if shift)
            s["planned_km"].append(dp)
            s["actual_km"].append(da)
            s["delta_km"].append(delta)
            if dp > 0:
                s["relative_delta_pct"].append(100 * delta / dp)
            s["lateness_minutes"].extend(late)
            s["early_minutes"].extend(early)
            if ordinary_span:
                s["sensitivity_lateness_minutes"].extend(late)
    print("QA:", quality)
    print("Anomaly examples:", anomaly_examples)
    for group, summary in summaries.items():
        print("Summary", group, dict(summary))
        print("Distribution", group, "[min,p05,p50,p90,p95,p99,max,mean]")
        for metric, values in samples[group].items():
            print(metric, distribution(values))
    for group in ("all", 0, 1):
        drivers = [v for (country, _), v in driver_counts.items() if group == "all" or country == group]
        eligible = [v for v in drivers if v["delivery_routes"] >= 20]
        print("Drivers", group, "total / changed / any late / >=20 eligible delivery routes:",
              len(drivers), sum(v["changed"] > 0 for v in drivers), sum(v["late_routes"] > 0 for v in drivers), len(eligible))
        print("Driver late-route percent distribution (>=20):",
              distribution([100 * v["late_routes"] / v["delivery_routes"] for v in eligible]))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

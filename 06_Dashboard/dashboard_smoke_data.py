"""Read the full-workbook dashboard overview over local PostgreSQL."""
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Overview:
    route_count: int
    eligible_delivery_count: int
    late_count: int
    late_delivery_rate: Decimal


def read_overview() -> Overview:
    import psycopg

    with psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=5432,
        dbname="p002_last_mile",
        user="p002_report",
        passfile=str(Path.home() / ".config" / "p002" / "pgpass"),
        connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    ) as connection:
        rows = connection.execute(
            """
            SELECT current_user, route_count, eligible_delivery_count, late_count, late_delivery_rate
            FROM reporting.dashboard_overview
            WHERE timing_cohort = %s
            """,
            ("full",),
        ).fetchall()

    if len(rows) != 1 or rows[0][0] != "p002_report":
        raise ValueError("The reporting overview must return exactly one full-workbook row as p002_report")
    _, routes, eligible, late, rate = rows[0]
    if (not all(type(value) is int for value in (routes, eligible, late))
            or routes < 0 or not 0 <= late <= eligible or eligible == 0
            or not isinstance(rate, Decimal) or not rate.is_finite()
            or not 0 <= rate <= 1 or abs(rate - Decimal(late) / eligible) > Decimal("1e-12")):
        raise ValueError("The overview returned invalid KPI counts or rate")
    return Overview(routes, eligible, late, rate)

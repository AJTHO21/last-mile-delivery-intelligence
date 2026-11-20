"""Offline unit checks, with an explicit opt-in for the live reporting read."""
import os
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "06_Dashboard"))
from dashboard_smoke_data import Overview, read_overview


class DashboardSmokeTests(unittest.TestCase):
    def read_fixture(self, rows):
        connector = MagicMock()
        session = connector.return_value.__enter__.return_value
        session.execute.return_value.fetchall.return_value = rows
        with patch.dict(sys.modules, {"psycopg": SimpleNamespace(connect=connector)}):
            result = read_overview()
        self.assertEqual(connector.call_args.kwargs["user"], "p002_report")
        self.assertEqual(connector.call_args.kwargs["hostaddr"], "127.0.0.1")
        self.assertNotIn("password", connector.call_args.kwargs)
        self.assertIn("default_transaction_read_only=on", connector.call_args.kwargs["options"])
        self.assertEqual(session.execute.call_args.args[1], ("full",))
        self.assertIn("reporting.dashboard_overview", session.execute.call_args.args[0])
        return result

    def test_full_overview_uses_reporting_role_and_formats_rate(self):
        rate = Decimal("0.11128837004157243269")
        row = self.read_fixture([("p002_report", 19647, 213122, 23718, rate)])
        self.assertEqual(row, Overview(19647, 213122, 23718, rate))
        self.assertEqual(f"{row.late_delivery_rate:.2%}", "11.13%")

    def test_rejects_missing_or_duplicate_rows(self):
        row = ("p002_report", 1, 1, 1, Decimal(1))
        for rows in ([], [row, row]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.read_fixture(rows)

    def test_rejects_wrong_role_or_inconsistent_metrics(self):
        for row in (("p002_dev", 1, 1, 1, Decimal(1)),
                    ("p002_report", 1, 0, 0, None),
                    ("p002_report", 1, 1, 1, Decimal("0.5")),
                    ("p002_report", 1, 1, 1, Decimal("NaN"))):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.read_fixture([row])

    @unittest.skipUnless(os.environ.get("P002_SMOKE_LIVE") == "1", "requires the live WSL reporting login")
    def test_live_overview(self):
        row = read_overview()
        self.assertEqual((row.route_count, row.eligible_delivery_count, row.late_count),
                         (19647, 213122, 23718))
        self.assertEqual(f"{row.late_delivery_rate:.2%}", "11.13%")


if __name__ == "__main__":
    unittest.main()

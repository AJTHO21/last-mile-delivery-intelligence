"""Executive data and native Streamlit rendering checks with synthetic fixtures."""
from decimal import Decimal as D
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

import psycopg
import streamlit as st
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[2] / "06_Dashboard"
sys.path.insert(0, str(DASHBOARD))
from executive_overview_data import ExecutiveData, read_executive_data


def fixture(cohort="full", available=True):
    overview = dict(
        timing_cohort=cohort, route_count=20, eligible_delivery_count=100,
        early_count=10, in_window_count=79, late_count=11,
        eligible_route_count=20, late_route_count=8,
        valid_sequence_route_count=20, changed_address_route_count=14,
        late_delivery_rate=D(".11"), late_route_rate=D(".4"), changed_address_route_rate=D(".7"),
        median_late_minutes=45.5, p90_late_minutes=120.1,
    )
    if cohort != "full":
        overview.update(eligible_delivery_count=90, late_count=9, in_window_count=71, late_delivery_rate=D(".10"))
    crude = dict(
        changed_eligible_route_count=14, unchanged_eligible_route_count=6,
        changed_late_route_count=5, unchanged_late_route_count=3,
        changed_route_rate=D(".357142857"), unchanged_route_rate=D(".5"),
        changed_eligible_delivery_count=70, unchanged_eligible_delivery_count=30,
        changed_late_delivery_count=7, unchanged_late_delivery_count=4,
        changed_delivery_rate=D(".1"), unchanged_delivery_rate=D(".133333333"),
    )
    standardized = dict(
        changed_route_rate=D(".4"), unchanged_route_rate=D(".42"),
        changed_delivery_rate=D(".11"), unchanged_delivery_rate=D(".12"),
        supported_strata=6, observed_strata=8,
        supported_pooled_eligible_routes=18, observed_pooled_eligible_routes=20,
    )
    removed = dict(timing_cohort="removed_over_1440", route_count=2, eligible_delivery_count=10, late_count=2)
    return ExecutiveData(overview, removed, crude, standardized if available else None)


class ExecutiveDataTests(unittest.TestCase):
    def test_loads_each_dataset_in_one_read_only_reporting_snapshot(self):
        data = fixture("span_at_most_1440")
        with patch("executive_overview_data.psycopg.connect") as connect:
            session = connect.return_value.__enter__.return_value
            ready, identity, overview, crude, standard = [MagicMock() for _ in range(5)]
            identity.fetchone.return_value = {"role": "p002_report"}
            overview.fetchall.return_value = [data.overview, data.removed]
            crude.fetchall.return_value = [data.crude]
            standard.fetchall.return_value = [data.standardized]
            session.execute.side_effect = [ready, identity, overview, crude, standard]
            self.assertEqual(read_executive_data("span_at_most_1440"), data)
            kw = connect.call_args.kwargs
            self.assertEqual((kw["hostaddr"], kw["user"]), ("127.0.0.1", "p002_report"))
            self.assertNotIn("password", kw)
            self.assertIn("READ ONLY", session.execute.call_args_list[0].args[0])
            for call, name in zip(session.execute.call_args_list[2:],
                                  ("dashboard_overview", "route_performance_comparison", "route_performance_standardized")):
                self.assertIn(f"reporting.{name}", call.args[0])
                self.assertEqual(call.args[1], ("span_at_most_1440",))
            self.assertIn("country IS NULL AND route_size_band IS NULL", session.execute.call_args_list[3].args[0])

    def test_invalid_cohort_cannot_open_a_connection(self):
        with patch("executive_overview_data.psycopg.connect") as connect:
            with self.assertRaises(ValueError):
                read_executive_data("removed_over_1440")
            connect.assert_not_called()

    def test_unexpected_database_role_is_rejected(self):
        with patch("executive_overview_data.psycopg.connect") as connect:
            session = connect.return_value.__enter__.return_value
            session.execute.return_value.fetchone.return_value = {"role": "p002_dev"}
            with self.assertRaisesRegex(ValueError, "role"):
                read_executive_data("full")
            self.assertEqual(session.execute.call_count, 2)

    @unittest.skipUnless(os.environ.get("P002_EXECUTIVE_LIVE") == "1", "requires the live WSL reporting login")
    def test_live_baselines(self):
        for cohort, expected in (("full", (19647, 213122, 23718, 6)),
                                 ("span_at_most_1440", (18479, 201796, 21748, 6))):
            with self.subTest(cohort=cohort):
                data = read_executive_data(cohort)
                self.assertEqual((data.overview["route_count"], data.overview["eligible_delivery_count"],
                                  data.overview["late_count"], data.standardized["supported_strata"]), expected)


class ExecutiveRenderingTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        self.app = AppTest.from_file(str(DASHBOARD / "executive_overview.py"), default_timeout=30)

    def test_renders_four_kpis_two_charts_and_updates_scope(self):
        with patch("executive_overview_data.read_executive_data", side_effect=fixture):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertEqual([metric.value for metric in self.app.metric], ["11.00%", "40.00%", "45.50 min", "70.00%"])
            self.assertEqual(len(self.app.get("vega_lite_chart")), 2)
            self.assertTrue(any("6 of 8 strata supported" in caption.value for caption in self.app.caption))
            self.assertTrue(any("Included in this view" in caption.value for caption in self.app.caption))
            timing = [widget for widget in self.app.selectbox if widget.label == "Timing cohort"]
            self.assertEqual(len(timing), 1)
            self.assertFalse(self.app.sidebar.selectbox)
            timing[0].select("span_at_most_1440").run()
            self.assertFalse(self.app.exception)
            self.assertEqual(self.app.metric[0].value, "10.00%")
            self.assertTrue(any("9 / 90" in caption.value for caption in self.app.caption))
            self.assertTrue(any("Excluded from this view" in caption.value for caption in self.app.caption))

    def test_missing_standardization_displays_unavailable(self):
        with patch("executive_overview_data.read_executive_data", return_value=fixture(available=False)):
            self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Standardized comparison unavailable" in caption.value for caption in self.app.caption))

    def test_connection_error_does_not_render_fake_values_or_error_details(self):
        with patch("executive_overview_data.read_executive_data", side_effect=psycopg.OperationalError("private detail")):
            self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.metric), 0)
        self.assertIn("reporting data is unavailable", self.app.error[0].value)
        self.assertNotIn("private detail", self.app.error[0].value)


if __name__ == "__main__":
    unittest.main()

"""Page 3 reporting contract and native Streamlit rendering checks."""
from contextlib import nullcontext
import json
import os

import psycopg
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[2] / "06_Dashboard"
sys.path.insert(0, str(DASHBOARD))
from distance_quality_data import read_quality_page, read_summary
from route_performance_data import RoutePage, Scope


class DistanceDataTests(unittest.TestCase):
    def test_summary_binds_rollup_dimensions_and_checks_grain(self):
        connection = MagicMock()
        rollup = {"distance_category": None, "route_count": 3}
        shorter = {"distance_category": "shorter", "route_count": 3}
        with patch("distance_quality_data.reporting_connection", return_value=nullcontext(connection)):
            connection.execute.return_value.fetchall.return_value = [rollup, shorter]
            self.assertEqual(read_summary(Scope("full", 0, "11–20"), "changed"), (rollup, {"shorter": shorter}))
            connection.execute.return_value.fetchall.return_value = [rollup, shorter, shorter]
            with self.assertRaises(ValueError):
                read_summary(Scope("full", 0, "11–20"), "changed")
        sql, params = connection.execute.call_args.args
        self.assertEqual(sql.count("IS NOT DISTINCT FROM"), 3)
        self.assertEqual(params, {"cohort": "full", "country": 0, "size": "11–20", "address": "changed"})

    def test_review_binds_filters_and_uses_bounded_route_grain(self):
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = list(range(26))
        with patch("distance_quality_data.reporting_connection", return_value=nullcontext(connection)):
            page = read_quality_page(Scope("span_at_most_1440", 1), None, "longer", "distance", "7545", 1)
            with self.assertRaises(ValueError):
                read_quality_page(Scope("full"), None, None, "all", "1 OR 1=1", 0)
        self.assertEqual((len(page.rows), page.has_next), (25, True))
        sql, params = connection.execute.call_args.args
        self.assertNotIn("JOIN", sql)
        self.assertNotIn("7545", sql)
        self.assertEqual((params["route_id"], params["limit"], params["offset"]), (7545, 26, 25))
        self.assertEqual(params["cohort"], "span_at_most_1440")

    @unittest.skipUnless(os.environ.get("P002_DISTANCE_LIVE") == "1", "requires the live WSL reporting login")
    def test_live_distance_controls_and_known_anomaly(self):
        rollup, categories = read_summary(Scope("full"), None)
        self.assertEqual([categories[k]["route_count"] for k in ("shorter", "equal", "longer")],
                         [7386, 5291, 6970])
        self.assertEqual(rollup["distance_review_route_count"], 98)
        self.assertAlmostEqual(rollup["median_signed_difference_km"], 0, places=2)
        retained, _ = read_summary(Scope("span_at_most_1440"), None)
        self.assertEqual(retained["route_count"], 18479)
        result = read_quality_page(Scope("full"), None, None, "distance", "7545", 0)
        self.assertEqual([row["route_id"] for row in result.rows], [7545])
        self.assertEqual(result.rows[0]["actual_same_address_nonzero_legs"], 1)


class DistanceRenderingTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def test_charts_scope_pagination_and_inspection(self):
        rollup = dict(route_count=3, distance_review_route_count=1, p05_signed_difference_km=-2,
                      median_signed_difference_km=0, p95_signed_difference_km=3)
        categories = {"longer": dict(route_count=3, late_route_count=1, eligible_route_count=2,
                                     late_route_rate=.5, late_delivery_count=2, eligible_delivery_count=8,
                                     late_delivery_rate=.25)}
        route = dict(route_id=1, import_id=1, country_name="Norway", route_size_band="1–5", visit_count=3,
                     address_sequence_status="changed", distance_category="longer", planned_geodesic_km=0,
                     actual_geodesic_km=2, signed_difference_km=2, absolute_difference_km=2,
                     distance_difference_pct=None, route_timing_span_over_1440=False, has_arrival_reversal=True,
                     zero_planned_distance=True, large_distance_gap=False, planned_same_address_nonzero_legs=0,
                     actual_same_address_nonzero_legs=1)
        with (patch("distance_quality_data.read_summary", return_value=(rollup, categories)) as summary,
              patch("distance_quality_data.read_quality_page",
                    side_effect=lambda *args: RoutePage([route], args[-1] == 0)) as review):
            app = AppTest.from_file(str(DASHBOARD / "distance_quality.py")).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("vega_lite_chart")), 4)
            self.assertEqual([metric.value for metric in app.metric], ["-2.00", "0.00", "3.00"])
            chart = json.loads(app.get("vega_lite_chart")[-1].proto.spec)
            self.assertEqual(chart["layer"][1]["encoding"]["y"]["sort"], ["P05", "Median", "P95"])
            self.assertIn("geodesic km", chart["layer"][1]["encoding"]["x"]["title"])
            self.assertNotIn("Planned km", app.dataframe[0].value.columns)
            self.assertTrue(any("2 / 8 eligible" in caption.value for caption in app.caption))
            app.button[1].click().run()
            self.assertEqual(review.call_args.args[-1], 1)
            app.text_input[0].set_value("1").run()
            self.assertEqual(review.call_args.args[-2:], ("1", 0))
            self.assertEqual(summary.call_count, 1)
            app.selectbox[-1].select((1, 1)).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[-1].value, "Unavailable")
            self.assertIn("Nonzero actual same-address leg", app.dataframe[0].value.iloc[0]["Review flags"])
            next(widget for widget in app.selectbox if widget.label == "Address order").select("changed").run()
            self.assertEqual(summary.call_args.args[1], "changed")
            self.assertIsNone(app.selectbox[-1].value)

    def test_navigation_uses_single_shared_sidebar_timing_control(self):
        with (patch("executive_overview_data.read_executive_data", side_effect=ValueError),
              patch("route_performance_data.read_comparison", return_value=[]) as comparison,
              patch("route_performance_data.read_displacement", return_value=[]),
              patch("route_performance_data.read_route_page", return_value=RoutePage([], False)),
              patch("distance_quality_data.read_summary", return_value=(None, {})) as summary,
              patch("distance_quality_data.read_quality_page", return_value=RoutePage([], False))):
            app = AppTest.from_file(str(DASHBOARD / "dashboard.py")).run()
            app.sidebar.selectbox[0].select("span_at_most_1440").run()
            app.switch_page("distance_quality.py").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, "Distance Deviations & Data Quality")
            self.assertEqual(summary.call_args.args[0].cohort, "span_at_most_1440")
            self.assertEqual(sum(widget.label == "Timing cohort" for widget in app.selectbox), 1)
            app.switch_page("route_performance.py").run()
            self.assertFalse(app.exception)
            self.assertEqual(comparison.call_args.args[0].cohort, "span_at_most_1440")
            app.sidebar.selectbox[0].select("full").run()
            app.switch_page("executive_overview.py").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.sidebar.selectbox[0].value, "full")

    def test_database_failure_does_not_expose_details_or_render_metrics(self):
        failure = psycopg.OperationalError("private detail")
        with (patch("distance_quality_data.read_summary", side_effect=failure),
              patch("distance_quality_data.read_quality_page", side_effect=failure)):
            app = AppTest.from_file(str(DASHBOARD / "distance_quality.py")).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.metric)
        self.assertEqual(len(app.error), 2)
        self.assertNotIn("private detail", str([error.value for error in app.error]))


if __name__ == "__main__":
    unittest.main()

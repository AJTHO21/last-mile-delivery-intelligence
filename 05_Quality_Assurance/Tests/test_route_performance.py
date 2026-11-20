"""Route page query and Streamlit interaction tests."""
from contextlib import nullcontext
from decimal import Decimal
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
from route_performance_data import (
    ROUTE_LIMIT, VISIT_LIMIT, RoutePage, Scope, read_comparison, read_displacement,
    read_route_page, read_visits, route_id_from_search,
)


class RouteDataTests(unittest.TestCase):
    def test_route_query_parameterizes_search_scope_and_page(self):
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = [{"route_id": i} for i in range(26)]
        with patch("route_performance_data.reporting_connection", return_value=nullcontext(connection)):
            page = read_route_page(Scope("span_at_most_1440", 0, "11–20"), "changed", "late", "7545", 2)
        self.assertEqual((len(page.rows), page.has_next), (ROUTE_LIMIT, True))
        query, params = connection.execute.call_args.args
        self.assertIn("FROM reporting.dashboard_route", query)
        self.assertNotIn("JOIN", query)
        self.assertNotIn("7545", query)
        self.assertEqual(params, dict(cohort="span_at_most_1440", country=0, size="11–20",
                                      address="changed", flag="late", route_id=7545, limit=26, offset=50))

    def test_drill_is_bounded_and_uses_both_route_keys(self):
        connection = MagicMock()
        with patch("route_performance_data.reporting_connection", return_value=nullcontext(connection)):
            read_visits(7545, 1, 2)
        query, params = connection.execute.call_args.args
        self.assertIn("WHERE route_id = %s AND import_id = %s", query)
        self.assertIn("ORDER BY index_a", query)
        self.assertEqual(params, (7545, 1, VISIT_LIMIT, 100))

    def test_aggregate_scope_is_bound_and_displacement_has_own_filters(self):
        connection = MagicMock()
        with patch("route_performance_data.reporting_connection", return_value=nullcontext(connection)):
            read_comparison(Scope("full", 1, "21+"))
            read_displacement("full", "unchanged", "changed_visit_order")
        comparison, displacement = connection.execute.call_args_list
        self.assertEqual(comparison.args[1], {"cohort": "full", "country": 1, "size": "21+"})
        self.assertEqual(displacement.args[1], ("full", "unchanged", "changed_visit_order"))
        self.assertNotIn("country =", displacement.args[0])

    def test_reader_rejects_wrong_role_before_any_data_read(self):
        with patch("route_performance_data.psycopg.connect") as connect:
            connection = connect.return_value.__enter__.return_value
            connection.execute.return_value.fetchone.return_value = {"role": "p002_dev"}
            with self.assertRaisesRegex(ValueError, "role"):
                read_comparison(Scope("full"))
            self.assertEqual(connection.execute.call_count, 2)
            self.assertEqual(connect.call_args.kwargs["user"], "p002_report")
            self.assertEqual(connect.call_args.kwargs["hostaddr"], "127.0.0.1")
            self.assertIn("default_transaction_read_only=on", connect.call_args.kwargs["options"])
            self.assertEqual(connection.execute.call_args_list[0].args, ("SET TRANSACTION READ ONLY",))
            self.assertNotIn("password", connect.call_args.kwargs)

    def test_search_rejects_invalid_values(self):
        for value in ("1 OR 1=1", "2147483648", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                route_id_from_search(value)
        self.assertEqual(route_id_from_search("0"), 0)
        self.assertIsNone(route_id_from_search(" "))

    @unittest.skipUnless(os.environ.get("P002_ROUTE_LIVE") == "1", "requires the live WSL reporting login")
    def test_live_page_and_drill(self):
        rows = read_comparison(Scope("full"))
        self.assertEqual(sum(row["changed_eligible_route_count"] + row["unchanged_eligible_route_count"] for row in rows),
                         19383)
        result = read_route_page(Scope("full"), None, None, "7545", 0)
        self.assertEqual([row["route_id"] for row in result.rows], [7545])
        row = result.rows[0]
        visits = read_visits(row["route_id"], row["import_id"], 0)
        self.assertEqual(len(visits), min(row["visit_count"], VISIT_LIMIT))
        self.assertEqual([visit["index_a"] for visit in visits], list(range(len(visits))))


class RouteRenderingTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def test_filters_pagination_and_selected_visit_render(self):
        route = dict(
            route_id=1, import_id=1, country_name="Norway", route_size_band="1–5", visit_count=3,
            address_sequence_status="changed", exact_visit_match=False, moved_visit_count=2,
            eligible_delivery_visit_count=2, late_delivery_visit_count=1, late_delivery_rate=Decimal(".5"),
            has_late_arrival=True, route_timing_span_over_1440=False, has_arrival_reversal=False,
            distance_review_flag=False,
        )
        visit = dict(
            index_p=2, index_a=1, stop_id=10, address_id=20, depot=False, delivery=True,
            earliest_minutes=1, arrived_minutes=4, latest_minutes=3, arrival_status="late",
            eligible_delivery=True, eligibility_reason="eligible_delivery", early_minutes=None, late_minutes=1,
            arrival_tie=False, arrival_reversal=True, zero_width_window=False, depot_delivery_overlap=False,
            route_timing_span_minutes=4, route_timing_span_over_1440=False,
            early_gap_over_1440=False, late_gap_over_1440=False, worksheet_name="Sheet1", source_row_number=2,
        )
        comparison = dict(country_name="Norway", route_size_band="1–5", changed_route_count=10,
                          unchanged_route_count=10, changed_eligible_route_count=10, unchanged_eligible_route_count=10,
                          changed_late_route_count=2, unchanged_late_route_count=3,
                          changed_route_rate=Decimal(".2"), unchanged_route_rate=Decimal(".3"))
        displacement = dict(displacement_band="1", visit_count=20, represented_route_count=8,
                            eligible_delivery_count=15, late_delivery_count=3, late_delivery_rate=Decimal(".2"))

        def get_page(scope, address, flag, search, page):
            return RoutePage([dict(route, route_id=2)] if page else [route], page == 0 and not search)

        with (patch("route_performance_data.read_comparison", return_value=[comparison]) as compare,
              patch("route_performance_data.read_displacement", return_value=[displacement]) as displace,
              patch("route_performance_data.read_route_page", side_effect=get_page) as pages,
              patch("route_performance_data.read_visits", return_value=[visit]) as drill):
            app = AppTest.from_file(str(DASHBOARD / "route_performance.py"), default_timeout=20).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("vega_lite_chart")), 2)
            self.assertIn("2 / 10", app.dataframe[0].value.iloc[0]["Changed"])
            app.button[1].click().run()
            self.assertEqual(pages.call_args.args[-1], 1)
            app.selectbox[1].select(0).run()
            self.assertEqual(pages.call_args.args[-1], 0)
            self.assertEqual(compare.call_args.args[0].country, 0)
            self.assertEqual(displace.call_count, 1)
            app.text_input[0].set_value("1").run()
            self.assertEqual(pages.call_args.args[3], "1")
            app.selectbox[-1].select((1, 1)).run()
            self.assertFalse(app.exception)
            self.assertEqual(drill.call_args.args, (1, 1, 0))
            self.assertEqual(list(app.dataframe[-3].value.columns),
                             ["Actual", "Planned", "Stop ID", "Address ID", "Outcome", "Late (min)", "Flags"])
            self.assertIn("Arrival (min)", app.dataframe[-2].value.columns)
            self.assertEqual(app.dataframe[-1].value.iloc[0]["Source row"], "Sheet1:2")
            self.assertEqual(app.dataframe[-3].value.iloc[0]["Flags"], "Reversal")
            self.assertEqual(app.dataframe[-3].value.iloc[0]["Actual"], 1)
            app.selectbox[0].select_index(1).run()
            self.assertEqual(compare.call_args.args[0].cohort, "span_at_most_1440")
            self.assertEqual(displace.call_args.args[0], "span_at_most_1440")
            self.assertEqual(app.selectbox[-1].value, None)

    def test_sidebar_timing_cohort_persists_in_both_directions(self):
        def assert_sidebar_timing(app, expected):
            timing = [widget for widget in app.selectbox if widget.label == "Timing cohort"]
            sidebar_timing = [widget for widget in app.sidebar.selectbox if widget.label == "Timing cohort"]
            self.assertEqual(len(timing), 1)
            self.assertEqual(len(sidebar_timing), 1)
            self.assertEqual(timing[0].key, sidebar_timing[0].key)
            self.assertEqual(sidebar_timing[0].value, expected)
            self.assertFalse(app.exception)
            return sidebar_timing[0]

        with (patch("executive_overview_data.read_executive_data", side_effect=ValueError) as overview,
              patch("route_performance_data.read_comparison", return_value=[]) as compare,
              patch("route_performance_data.read_displacement", return_value=[]),
              patch("route_performance_data.read_route_page", return_value=RoutePage([], False))):
            app = AppTest.from_file(str(DASHBOARD / "dashboard.py")).run()
            self.assertEqual(app.title[0].value, "Executive Overview")
            assert_sidebar_timing(app, "full").select("span_at_most_1440").run()

            app.switch_page("route_performance.py").run()
            self.assertEqual(app.title[0].value, "Route Performance & Exceptions")
            assert_sidebar_timing(app, "span_at_most_1440")
            self.assertEqual(compare.call_args.args[0].cohort, "span_at_most_1440")

            assert_sidebar_timing(app, "span_at_most_1440").select("full").run()
            self.assertEqual(compare.call_args.args[0].cohort, "full")
            app.switch_page("executive_overview.py").run()
            self.assertEqual(app.title[0].value, "Executive Overview")
            assert_sidebar_timing(app, "full")
            overview.assert_called_with("full")

    def test_database_failure_displays_no_private_details(self):
        failure = psycopg.OperationalError("private detail")
        with (patch("route_performance_data.read_comparison", side_effect=failure),
              patch("route_performance_data.read_displacement", side_effect=failure),
              patch("route_performance_data.read_route_page", side_effect=failure)):
            app = AppTest.from_file(str(DASHBOARD / "route_performance.py")).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 3)
        self.assertNotIn("private detail", str([error.value for error in app.error]))


if __name__ == "__main__":
    unittest.main()

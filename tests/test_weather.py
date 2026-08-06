"""Property-based tests for weather.py using Hypothesis."""

import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Smoke tests for get_coordinates — task 3.1
# These tests mock requests to avoid real network calls and verify every
# error path (requirements 3.1, 3.2, 3.3).
# ---------------------------------------------------------------------------

class TestGetCoordinates(unittest.TestCase):
    """Smoke tests for get_coordinates covering all error and success paths."""

    def _make_ok_response(self, lat: float, lon: float) -> MagicMock:
        """Return a mock requests.Response with a valid geocoding payload."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [{"latitude": lat, "longitude": lon, "name": "Test City"}]
        }
        return mock_resp

    # --- success path ---

    @patch("weather.requests.get")
    def test_success_returns_float_tuple(self, mock_get):
        """On a valid response, get_coordinates returns (float, float)."""
        mock_get.return_value = self._make_ok_response(40.7484, -73.9967)

        from weather import get_coordinates
        result = get_coordinates("10001")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 40.7484)
        self.assertAlmostEqual(result[1], -73.9967)

    @patch("weather.requests.get")
    def test_success_uses_first_result(self, mock_get):
        """When multiple results are returned, only the first is used."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [
                {"latitude": 1.0, "longitude": 2.0},
                {"latitude": 99.0, "longitude": 99.0},
            ]
        }
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        lat, lon = get_coordinates("10001")

        self.assertAlmostEqual(lat, 1.0)
        self.assertAlmostEqual(lon, 2.0)

    # --- network error path (requirement 3.3) ---

    @patch("weather.requests.get")
    def test_network_error_exits_1(self, mock_get):
        """A network error prints to stderr and exits with code 1."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("connection refused")

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("10001")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    # --- zero results path (requirement 3.2) ---

    @patch("weather.requests.get")
    def test_empty_results_exits_1(self, mock_get):
        """An empty results list prints to stderr and exits with code 1."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("00000")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    @patch("weather.requests.get")
    def test_missing_results_key_exits_1(self, mock_get):
        """A response with no 'results' key prints to stderr and exits with code 1."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {}  # no 'results' key at all
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("00000")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    # --- malformed response path (requirement 3.2 / 3.3) ---

    @patch("weather.requests.get")
    def test_missing_latitude_exits_1(self, mock_get):
        """A result missing 'latitude' prints a descriptive error and exits 1."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [{"longitude": -73.9967}]  # latitude missing
        }
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("10001")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    @patch("weather.requests.get")
    def test_missing_longitude_exits_1(self, mock_get):
        """A result missing 'longitude' prints a descriptive error and exits 1."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [{"latitude": 40.7484}]  # longitude missing
        }
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("10001")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    @patch("weather.requests.get")
    def test_none_lat_lon_exits_1(self, mock_get):
        """None values for latitude/longitude produce a descriptive error and exit 1."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [{"latitude": None, "longitude": None}]
        }
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("10001")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    # --- HTTP error path ---

    @patch("weather.requests.get")
    def test_http_error_exits_1(self, mock_get):
        """An HTTP 4xx/5xx response prints to stderr and exits with code 1."""
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_resp

        from weather import get_coordinates
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_coordinates("10001")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    # --- correct API call parameters ---

    @patch("weather.requests.get")
    def test_correct_url_and_params(self, mock_get):
        """get_coordinates calls the geocoding URL with the required params."""
        mock_get.return_value = self._make_ok_response(40.0, -74.0)

        from weather import get_coordinates
        get_coordinates("90210")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args

        # positional arg 0 is the URL
        url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", "")
        self.assertIn("geocoding-api.open-meteo.com", url)

        params = call_kwargs[1].get("params", {})
        self.assertEqual(params.get("name"), "90210")
        self.assertEqual(params.get("count"), 1)
        self.assertEqual(params.get("language"), "en")
        self.assertEqual(params.get("format"), "json")
        self.assertEqual(call_kwargs[1].get("timeout"), 10)


# ---------------------------------------------------------------------------
# Smoke tests for find_current_hour_index — task 4.1
# Pure function; no network calls needed. Covers the three lookup paths
# described in the spec (requirements 4.1).
# ---------------------------------------------------------------------------

class TestFindCurrentHourIndex(unittest.TestCase):
    """Smoke tests for find_current_hour_index (requirement 4.1)."""

    # --- helper ---

    @staticmethod
    def _current_utc_hour_str() -> str:
        """Return the exact ISO 8601 string the function looks for right now."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        return now.strftime("%Y-%m-%dT%H:00")

    @staticmethod
    def _current_utc_hour() -> int:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).hour

    # --- path 1: exact date+hour match ---

    def test_exact_match_returns_correct_index(self):
        """Returns the index of the entry whose full timestamp matches now."""
        from weather import find_current_hour_index

        current = self._current_utc_hour_str()
        # Place the matching entry at position 2 out of 4
        times = [
            "1999-01-01T00:00",
            "1999-01-01T01:00",
            current,
            "1999-01-01T03:00",
        ]
        self.assertEqual(find_current_hour_index(times), 2)

    def test_exact_match_at_index_zero(self):
        """Works correctly when the matching entry is at the start of the list."""
        from weather import find_current_hour_index

        current = self._current_utc_hour_str()
        times = [current, "1999-01-01T01:00", "1999-01-01T02:00"]
        self.assertEqual(find_current_hour_index(times), 0)

    def test_exact_match_at_last_index(self):
        """Works correctly when the matching entry is at the end of the list."""
        from weather import find_current_hour_index

        current = self._current_utc_hour_str()
        times = ["1999-01-01T00:00", "1999-01-01T01:00", current]
        self.assertEqual(find_current_hour_index(times), 2)

    # --- path 2: hour-of-day fallback ---

    def test_fallback_by_hour_of_day(self):
        """When no exact date match exists, falls back to matching the hour component."""
        from weather import find_current_hour_index

        h = self._current_utc_hour()
        # Build a list where the hour-of-day matches but the date is wrong.
        # Use a past date so it can never be an exact match.
        fallback_entry = f"1990-06-15T{h:02d}:00"
        other_hour = (h + 1) % 24
        times = [
            f"1990-06-15T{other_hour:02d}:00",
            fallback_entry,
        ]
        self.assertEqual(find_current_hour_index(times), 1)

    # --- path 3: no match at all → return 0 ---

    def test_no_match_returns_zero(self):
        """Returns 0 when no entry matches either by full timestamp or hour-of-day."""
        from weather import find_current_hour_index

        h = self._current_utc_hour()
        # Build a list that has no entry for the current hour; use only the
        # two adjacent hours on the old date.
        other1 = (h + 1) % 24
        other2 = (h + 2) % 24
        times = [
            f"1990-06-15T{other1:02d}:00",
            f"1990-06-15T{other2:02d}:00",
        ]
        self.assertEqual(find_current_hour_index(times), 0)

    def test_empty_list_returns_zero(self):
        """Returns 0 for an empty times list."""
        from weather import find_current_hour_index
        self.assertEqual(find_current_hour_index([]), 0)

    def test_invalid_entries_skipped_in_fallback(self):
        """Malformed timestamp strings are skipped silently during fallback."""
        from weather import find_current_hour_index

        h = self._current_utc_hour()
        valid_fallback = f"1990-06-15T{h:02d}:00"
        times = ["not-a-date", "also-bad", valid_fallback]
        # Exact match fails → fallback skips bad entries → lands on index 2
        self.assertEqual(find_current_hour_index(times), 2)


# ---------------------------------------------------------------------------
# Smoke tests for get_weather — task 5.1
# These tests mock requests to avoid real network calls and verify every
# error path and the success path (requirements 4.1, 4.2, 4.3, 4.4).
# ---------------------------------------------------------------------------

class TestGetWeather(unittest.TestCase):
    """Smoke tests for get_weather covering all error and success paths."""

    def _make_ok_response(self, temps=None, rain=None, times=None) -> MagicMock:
        """Return a mock requests.Response with a valid weather payload."""
        from datetime import datetime, timezone
        current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        current_str = current_hour.strftime("%Y-%m-%dT%H:00")

        if times is None:
            times = [current_str]
        if temps is None:
            temps = [72.5]
        if rain is None:
            rain = [15]

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "hourly": {
                "time": times,
                "temperature_2m": temps,
                "precipitation_probability": rain,
            }
        }
        return mock_resp

    # --- success path ---

    @patch("weather.requests.get")
    def test_success_returns_float_and_int(self, mock_get):
        """On a valid response, get_weather returns (float, int)."""
        mock_get.return_value = self._make_ok_response(temps=[68.3], rain=[20])

        from weather import get_weather
        result = get_weather(40.7484, -73.9967)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], float)
        self.assertIsInstance(result[1], int)
        self.assertAlmostEqual(result[0], 68.3, places=1)
        self.assertEqual(result[1], 20)

    # --- network error path (requirement 4.3) ---

    @patch("weather.requests.get")
    def test_network_error_prints_to_stderr_and_exits_1(self, mock_get):
        """A network error prints to stderr and exits with code 1."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("timeout")

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    @patch("weather.requests.get")
    def test_http_error_exits_1(self, mock_get):
        """An HTTP error response prints to stderr and exits with code 1."""
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Error", stderr_capture.getvalue())

    # --- missing field paths (requirement 4.4) ---

    @patch("weather.requests.get")
    def test_missing_hourly_key_exits_1_with_field_name(self, mock_get):
        """A response missing the 'hourly' key exits 1 and stderr names the field."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {}  # no 'hourly' key
        mock_get.return_value = mock_resp

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        err_text = stderr_capture.getvalue()
        self.assertIn("Error", err_text)
        self.assertIn("hourly", err_text)

    @patch("weather.requests.get")
    def test_missing_time_key_exits_1_with_field_name(self, mock_get):
        """A response missing 'time' inside hourly exits 1 and stderr names the field."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "hourly": {
                "temperature_2m": [72.0],
                "precipitation_probability": [10],
                # 'time' is missing
            }
        }
        mock_get.return_value = mock_resp

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        err_text = stderr_capture.getvalue()
        self.assertIn("Error", err_text)
        self.assertIn("time", err_text)

    @patch("weather.requests.get")
    def test_missing_temperature_2m_key_exits_1_with_field_name(self, mock_get):
        """A response missing 'temperature_2m' exits 1 and stderr names the field."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "precipitation_probability": [10],
                # 'temperature_2m' is missing
            }
        }
        mock_get.return_value = mock_resp

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        err_text = stderr_capture.getvalue()
        self.assertIn("Error", err_text)
        self.assertIn("temperature_2m", err_text)

    @patch("weather.requests.get")
    def test_missing_precipitation_probability_key_exits_1_with_field_name(self, mock_get):
        """A response missing 'precipitation_probability' exits 1 and stderr names the field."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "temperature_2m": [72.0],
                # 'precipitation_probability' is missing
            }
        }
        mock_get.return_value = mock_resp

        from weather import get_weather
        stderr_capture = StringIO()

        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", stderr_capture):
                get_weather(40.7484, -73.9967)

        self.assertEqual(ctx.exception.code, 1)
        err_text = stderr_capture.getvalue()
        self.assertIn("Error", err_text)
        self.assertIn("precipitation_probability", err_text)

    # --- correct API call parameters (requirements 4.1, 4.2) ---

    @patch("weather.requests.get")
    def test_correct_api_params(self, mock_get):
        """get_weather calls the forecast URL with all required parameters."""
        mock_get.return_value = self._make_ok_response()

        from weather import get_weather
        get_weather(51.5074, -0.1278)

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args

        url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", "")
        self.assertIn("api.open-meteo.com", url)
        self.assertIn("forecast", url)

        params = call_kwargs[1].get("params", {})
        self.assertAlmostEqual(params.get("latitude"), 51.5074)
        self.assertAlmostEqual(params.get("longitude"), -0.1278)
        self.assertIn("temperature_2m", params.get("hourly", ""))
        self.assertIn("precipitation_probability", params.get("hourly", ""))
        self.assertEqual(params.get("temperature_unit"), "fahrenheit")
        self.assertEqual(params.get("forecast_days"), 1)
        self.assertEqual(call_kwargs[1].get("timeout"), 10)


# ---------------------------------------------------------------------------
# Smoke tests for get_advisory — task 7.1
# These tests mock requests to avoid real network calls and verify:
#   - success path with severity ranking and ASCII sanitization
#   - empty features list → None
#   - missing "features" key → None + stdout warning
#   - network error → None + stdout warning (not stderr, non-fatal)
#   - severity ranking: Extreme > Severe > Moderate > Minor > Unknown
#   - ties preserved by response order (min returns first matching element)
#   - description capped at 500 chars before sanitization
# Requirements: 8.1, 8.2, 8.3, 8.5, 8.6, 8.7
# ---------------------------------------------------------------------------

class TestGetAdvisory(unittest.TestCase):
    """Smoke tests for get_advisory covering all paths (requirements 8.1–8.7)."""

    def _make_feature(self, event, severity, headline, description):
        """Build a minimal NWS GeoJSON feature dict."""
        return {
            "properties": {
                "event": event,
                "severity": severity,
                "headline": headline,
                "description": description,
            }
        }

    def _make_ok_response(self, features):
        """Return a mock requests.Response with a valid NWS alerts payload."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"features": features}
        return mock_resp

    # --- success path: single alert ---

    @patch("weather.requests.get")
    def test_success_single_alert_returns_dict(self, mock_get):
        """A single alert returns a dict with the four expected keys."""
        feature = self._make_feature("Tornado Warning", "Extreme", "Tornado Warning in effect", "Take shelter now.")
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertIsNotNone(result)
        self.assertEqual(result["event"], "Tornado Warning")
        self.assertEqual(result["severity"], "Extreme")
        self.assertEqual(result["headline"], "Tornado Warning in effect")
        self.assertEqual(result["description"], "Take shelter now.")

    # --- no active alerts (empty features list) ---

    @patch("weather.requests.get")
    def test_empty_features_returns_none(self, mock_get):
        """When features list is empty, get_advisory returns None without warning."""
        mock_get.return_value = self._make_ok_response([])

        from weather import get_advisory
        stdout_capture = StringIO()
        with patch("sys.stdout", stdout_capture):
            result = get_advisory(40.0, -75.0)

        self.assertIsNone(result)
        # No warning should be printed for the "no alerts" case
        self.assertEqual(stdout_capture.getvalue(), "")

    # --- missing "features" key → None + stdout warning (req 8.6) ---

    @patch("weather.requests.get")
    def test_missing_features_key_returns_none_with_stdout_warning(self, mock_get):
        """A response missing the 'features' key prints a warning to stdout and returns None."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"something_else": []}  # no 'features' key
        mock_get.return_value = mock_resp

        from weather import get_advisory
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.stdout", stdout_capture):
            with patch("sys.stderr", stderr_capture):
                result = get_advisory(40.0, -75.0)

        self.assertIsNone(result)
        # Warning must go to stdout, not stderr
        self.assertIn("Warning", stdout_capture.getvalue())
        self.assertEqual(stderr_capture.getvalue(), "")

    # --- network error → None + stdout warning, non-fatal (req 8.5) ---

    @patch("weather.requests.get")
    def test_network_error_returns_none_non_fatal(self, mock_get):
        """A network error prints a warning to stdout, returns None, and does not exit."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("connection refused")

        from weather import get_advisory
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.stdout", stdout_capture):
            with patch("sys.stderr", stderr_capture):
                # Must NOT raise SystemExit
                result = get_advisory(40.0, -75.0)

        self.assertIsNone(result)
        # Warning to stdout, nothing to stderr
        self.assertIn("Warning", stdout_capture.getvalue())
        self.assertEqual(stderr_capture.getvalue(), "")

    @patch("weather.requests.get")
    def test_http_error_returns_none_non_fatal(self, mock_get):
        """An HTTP error prints a warning to stdout, returns None, and does not exit."""
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_resp

        from weather import get_advisory
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.stdout", stdout_capture):
            with patch("sys.stderr", stderr_capture):
                result = get_advisory(40.0, -75.0)

        self.assertIsNone(result)
        self.assertIn("Warning", stdout_capture.getvalue())
        self.assertEqual(stderr_capture.getvalue(), "")

    # --- severity ranking (req 8.2) ---

    @patch("weather.requests.get")
    def test_severity_ranking_extreme_wins(self, mock_get):
        """Extreme-severity alert is selected over Severe, Moderate, Minor, Unknown."""
        features = [
            self._make_feature("Minor Event", "Minor", "minor", "minor desc"),
            self._make_feature("Extreme Event", "Extreme", "extreme", "extreme desc"),
            self._make_feature("Severe Event", "Severe", "severe", "severe desc"),
        ]
        mock_get.return_value = self._make_ok_response(features)

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertIsNotNone(result)
        self.assertEqual(result["severity"], "Extreme")
        self.assertEqual(result["event"], "Extreme Event")

    @patch("weather.requests.get")
    def test_severity_ranking_order_extreme_severe_moderate_minor_unknown(self, mock_get):
        """Severity precedence: Extreme > Severe > Moderate > Minor > Unknown."""
        # Without Extreme present, Severe should win
        features = [
            self._make_feature("Unknown Event", "Unknown", "unknown", "u"),
            self._make_feature("Severe Event", "Severe", "severe", "s"),
            self._make_feature("Moderate Event", "Moderate", "moderate", "m"),
            self._make_feature("Minor Event", "Minor", "minor", "mn"),
        ]
        mock_get.return_value = self._make_ok_response(features)

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertEqual(result["severity"], "Severe")

    @patch("weather.requests.get")
    def test_severity_tie_uses_first_in_response_order(self, mock_get):
        """When two alerts have the same severity, the first in response order is used."""
        features = [
            self._make_feature("First Severe", "Severe", "first headline", "first desc"),
            self._make_feature("Second Severe", "Severe", "second headline", "second desc"),
        ]
        mock_get.return_value = self._make_ok_response(features)

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertEqual(result["event"], "First Severe")
        self.assertEqual(result["headline"], "first headline")

    @patch("weather.requests.get")
    def test_unknown_severity_treated_as_lowest(self, mock_get):
        """An alert with unknown/unrecognized severity is ranked lower than Minor."""
        features = [
            self._make_feature("Unrecognized", "SuperDuperBad", "headline", "desc"),
            self._make_feature("Minor Alert", "Minor", "minor headline", "minor desc"),
        ]
        mock_get.return_value = self._make_ok_response(features)

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        # Minor (rank 3) beats unrecognized (rank 4 via default)
        self.assertEqual(result["severity"], "Minor")

    # --- ASCII sanitization (req 8.7) ---

    @patch("weather.requests.get")
    def test_ascii_sanitization_non_ascii_replaced(self, mock_get):
        """Non-ASCII characters in advisory text are replaced so output is U+0020-U+007E only."""
        feature = self._make_feature(
            "Tornado \u26a0 Warning",   # ⚠ is non-ASCII
            "Severe",
            "Headline with \u00e9l\u00e9vation",  # é characters
            "Description with \u2603 snowman and caf\u00e9",  # ☃ and é
        )
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertIsNotNone(result)
        for key, value in result.items():
            for ch in value:
                self.assertTrue(
                    0x20 <= ord(ch) <= 0x7E,
                    f"Non-ASCII char {ch!r} (U+{ord(ch):04X}) found in result[{key!r}]"
                )

    @patch("weather.requests.get")
    def test_ascii_sanitization_pure_ascii_unchanged(self, mock_get):
        """Advisory text that is already pure ASCII is returned unchanged."""
        feature = self._make_feature(
            "Flash Flood Warning",
            "Moderate",
            "Flash Flood Warning until 8 PM EDT",
            "Rivers and streams may overflow their banks.",
        )
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertEqual(result["event"], "Flash Flood Warning")
        self.assertEqual(result["headline"], "Flash Flood Warning until 8 PM EDT")
        self.assertEqual(result["description"], "Rivers and streams may overflow their banks.")

    # --- description capped at 500 chars (req 8.3) ---

    @patch("weather.requests.get")
    def test_description_capped_at_500_chars(self, mock_get):
        """Description is capped to at most 500 characters."""
        long_desc = "A" * 1000
        feature = self._make_feature("Flood Warning", "Moderate", "headline", long_desc)
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertIsNotNone(result)
        self.assertLessEqual(len(result["description"]), 500)

    @patch("weather.requests.get")
    def test_description_exactly_500_chars_not_truncated_further(self, mock_get):
        """A description of exactly 500 chars is returned as-is."""
        exact_desc = "B" * 500
        feature = self._make_feature("Wind Advisory", "Minor", "headline", exact_desc)
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertEqual(len(result["description"]), 500)

    # --- correct API call (req 8.1) ---

    @patch("weather.requests.get")
    def test_correct_url_and_headers(self, mock_get):
        """get_advisory calls the NWS alerts URL with the required Accept header and timeout."""
        feature = self._make_feature("Test", "Minor", "h", "d")
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        get_advisory(40.7484, -73.9967)

        mock_get.assert_called_once()
        call_args = mock_get.call_args

        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        self.assertIn("api.weather.gov/alerts/active", url)
        self.assertIn("40.7484", url)
        self.assertIn("-73.9967", url)

        headers = call_args[1].get("headers", {})
        self.assertEqual(headers.get("Accept"), "application/geo+json")
        self.assertEqual(call_args[1].get("timeout"), 10)

    # --- None fields handled gracefully ---

    @patch("weather.requests.get")
    def test_none_field_values_sanitized_to_empty_string(self, mock_get):
        """None values for event/severity/headline/description are sanitized to empty strings."""
        feature = {
            "properties": {
                "event": None,
                "severity": None,
                "headline": None,
                "description": None,
            }
        }
        mock_get.return_value = self._make_ok_response([feature])

        from weather import get_advisory
        result = get_advisory(40.0, -75.0)

        self.assertIsNotNone(result)
        for key in ("event", "severity", "headline", "description"):
            self.assertIsInstance(result[key], str)
            # All chars must still be in valid ASCII range
            for ch in result[key]:
                self.assertTrue(0x20 <= ord(ch) <= 0x7E)


# ---------------------------------------------------------------------------
# Smoke tests for print_weather — task 8.1
# These tests capture stdout and verify the output format matches the spec
# (requirements 5.1, 5.2, 5.3, 8.3, 8.4, 8.7).
# ---------------------------------------------------------------------------

class TestPrintWeather(unittest.TestCase):
    """Smoke tests for print_weather covering all output format requirements."""

    def _capture_output(self, *args, **kwargs):
        """Call print_weather with given args and return the captured stdout lines."""
        from weather import print_weather
        buf = StringIO()
        with patch("sys.stdout", buf):
            print_weather(*args, **kwargs)
        return buf.getvalue().splitlines()

    # --- 1. Correct labels ---

    def test_correct_labels_present(self):
        """Output always contains the required 'Location: ', 'Temperature: ', 'Chance of Rain: ' labels."""
        lines = self._capture_output("90210", 72.5, 15)
        labels = [line.split(":")[0] + ":" for line in lines]
        self.assertIn("Location:", labels)
        # Temperature and Chance of Rain lines contain their label as prefix
        self.assertTrue(any(line.startswith("Temperature: ") for line in lines))
        self.assertTrue(any(line.startswith("Chance of Rain: ") for line in lines))

    # --- 2. Temperature formatted with 1 decimal + "degF" ---

    def test_temperature_format_one_decimal_degF(self):
        """Temperature line is formatted as '{value:.1f}degF'."""
        lines = self._capture_output("10001", 68.0, 0)
        temp_line = next(l for l in lines if l.startswith("Temperature: "))
        # Should end with 'degF' and the value should have exactly one decimal place
        self.assertTrue(temp_line.endswith("degF"), f"Expected degF suffix: {temp_line!r}")
        value_str = temp_line.removeprefix("Temperature: ").removesuffix("degF")
        # Must parse as a float and have one decimal digit
        value = float(value_str)
        self.assertAlmostEqual(value, 68.0, places=1)
        self.assertIn(".", value_str, "Temperature value must contain a decimal point")
        decimal_part = value_str.split(".")[1]
        self.assertEqual(len(decimal_part), 1, f"Expected exactly 1 decimal digit, got: {decimal_part!r}")

    def test_temperature_rounded_to_one_decimal(self):
        """A temperature like 72.567 is displayed as '72.6degF'."""
        lines = self._capture_output("10001", 72.567, 10)
        temp_line = next(l for l in lines if l.startswith("Temperature: "))
        self.assertIn("72.6degF", temp_line)

    # --- 3. Rain formatted as percentage ---

    def test_rain_formatted_as_percentage(self):
        """Chance of Rain line ends with '%' and contains the integer value."""
        lines = self._capture_output("10001", 70.0, 42)
        rain_line = next(l for l in lines if l.startswith("Chance of Rain: "))
        self.assertTrue(rain_line.endswith("%"), f"Expected '%' suffix: {rain_line!r}")
        value_str = rain_line.removeprefix("Chance of Rain: ").removesuffix("%")
        self.assertEqual(int(value_str), 42)

    # --- 4. advisory=None → "Advisory: No active advisories" ---

    def test_no_advisory_prints_no_active_advisories(self):
        """When advisory is None, prints 'Advisory: No active advisories'."""
        lines = self._capture_output("10001", 70.0, 10, advisory=None)
        self.assertIn("Advisory: No active advisories", lines)

    def test_no_advisory_does_not_print_advisory_fields(self):
        """When advisory is None, none of the Advisory Event/Severity/Headline/Description lines appear."""
        lines = self._capture_output("10001", 70.0, 10, advisory=None)
        for line in lines:
            self.assertFalse(line.startswith("Advisory Event:"), f"Unexpected line: {line!r}")
            self.assertFalse(line.startswith("Advisory Severity:"), f"Unexpected line: {line!r}")
            self.assertFalse(line.startswith("Advisory Headline:"), f"Unexpected line: {line!r}")
            self.assertFalse(line.startswith("Advisory Description:"), f"Unexpected line: {line!r}")

    # --- 5. advisory dict → all four advisory lines printed ---

    def test_advisory_dict_prints_all_four_lines(self):
        """When advisory is a dict, all four labeled advisory lines appear in output."""
        advisory = {
            "event": "Tornado Warning",
            "severity": "Extreme",
            "headline": "Tornado Warning in effect until 9 PM",
            "description": "A tornado has been spotted. Take shelter immediately.",
        }
        lines = self._capture_output("90210", 85.0, 60, advisory=advisory)

        event_lines = [l for l in lines if l.startswith("Advisory Event: ")]
        severity_lines = [l for l in lines if l.startswith("Advisory Severity: ")]
        headline_lines = [l for l in lines if l.startswith("Advisory Headline: ")]
        desc_lines = [l for l in lines if l.startswith("Advisory Description: ")]

        self.assertEqual(len(event_lines), 1, "Expected exactly one 'Advisory Event:' line")
        self.assertEqual(len(severity_lines), 1, "Expected exactly one 'Advisory Severity:' line")
        self.assertEqual(len(headline_lines), 1, "Expected exactly one 'Advisory Headline:' line")
        self.assertEqual(len(desc_lines), 1, "Expected exactly one 'Advisory Description:' line")

        self.assertIn("Tornado Warning", event_lines[0])
        self.assertIn("Extreme", severity_lines[0])
        self.assertIn("Tornado Warning in effect until 9 PM", headline_lines[0])
        self.assertIn("Take shelter immediately.", desc_lines[0])

    def test_advisory_dict_does_not_print_no_advisories_line(self):
        """When advisory is a dict, 'Advisory: No active advisories' is NOT printed."""
        advisory = {
            "event": "Flood Watch",
            "severity": "Moderate",
            "headline": "Flood Watch in effect",
            "description": "Heavy rain expected.",
        }
        lines = self._capture_output("10001", 65.0, 80, advisory=advisory)
        self.assertNotIn("Advisory: No active advisories", lines)

    # --- 6. All output characters are in U+0020–U+007E ---

    def test_output_ascii_only_no_advisory(self):
        """All characters in output (no advisory) are in U+0020–U+007E range."""
        lines = self._capture_output("10001", 73.2, 25, advisory=None)
        for line in lines:
            for ch in line:
                self.assertTrue(
                    0x20 <= ord(ch) <= 0x7E,
                    f"Non-printable-ASCII char {ch!r} (U+{ord(ch):04X}) found in output"
                )

    def test_output_ascii_only_with_advisory(self):
        """All characters in output (with advisory containing only ASCII text) are in U+0020–U+007E."""
        advisory = {
            "event": "Winter Storm Warning",
            "severity": "Severe",
            "headline": "Winter Storm Warning until 6 AM",
            "description": "Heavy snow of 8-12 inches expected.",
        }
        lines = self._capture_output("10001", 28.5, 90, advisory=advisory)
        for line in lines:
            for ch in line:
                self.assertTrue(
                    0x20 <= ord(ch) <= 0x7E,
                    f"Non-printable-ASCII char {ch!r} (U+{ord(ch):04X}) found in output"
                )

    def test_output_ascii_only_with_pre_sanitized_advisory(self):
        """Output is ASCII-safe even when advisory values contain only printable ASCII (as get_advisory guarantees)."""
        # get_advisory sanitizes text; print_weather must pass it through unchanged
        advisory = {
            "event": "High Wind Advisory",
            "severity": "Minor",
            "headline": "High Wind Advisory from 3 PM to 9 PM",
            "description": "Gusts up to 45 mph possible. Secure outdoor objects.",
        }
        lines = self._capture_output("77001", 95.3, 5, advisory=advisory)
        for line in lines:
            for ch in line:
                self.assertTrue(0x20 <= ord(ch) <= 0x7E)


# ---------------------------------------------------------------------------
# Smoke tests for main() — task 9.1
# These tests mock all external calls and verify pipeline wiring and CLI
# behavior (requirements 1.1, 1.2, 2.1, 2.2, 2.3, 4.1, 8.1).
# ---------------------------------------------------------------------------

class TestMain(unittest.TestCase):
    """Smoke tests for main() covering CLI arg handling and pipeline wiring."""

    def _run_main(self, argv=None):
        """
        Invoke main() with given sys.argv list (excluding script name).
        Returns (stdout_str, stderr_str).
        All external calls are mocked with fixed return values.
        """
        import weather

        full_argv = ["weather.py"] + (argv or [])
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.argv", full_argv), \
             patch("sys.stdout", stdout_capture), \
             patch("sys.stderr", stderr_capture), \
             patch("weather.get_coordinates", return_value=(40.7484, -73.9967)) as mock_coords, \
             patch("weather.get_weather", return_value=(72.5, 15)) as mock_weather, \
             patch("weather.get_advisory", return_value=None) as mock_advisory:
            weather.main()

        return stdout_capture.getvalue(), stderr_capture.getvalue()

    # --- 1. No args → uses DEFAULT_ZIP ---

    def test_no_args_uses_default_zip(self):
        """With no CLI args, main() uses DEFAULT_ZIP and prints 'Location: {DEFAULT_ZIP}'."""
        from weather import DEFAULT_ZIP
        stdout, _ = self._run_main(argv=[])
        self.assertIn(f"Location: {DEFAULT_ZIP}", stdout)

    def test_no_args_calls_all_pipeline_functions(self):
        """With no CLI args, main() calls validate_zip, get_coordinates, get_weather, get_advisory, print_weather."""
        import weather

        with patch("sys.argv", ["weather.py"]), \
             patch("sys.stdout", StringIO()), \
             patch("sys.stderr", StringIO()), \
             patch("weather.validate_zip", wraps=weather.validate_zip) as mock_validate, \
             patch("weather.get_coordinates", return_value=(40.7484, -73.9967)) as mock_coords, \
             patch("weather.get_weather", return_value=(72.5, 15)) as mock_weather, \
             patch("weather.get_advisory", return_value=None) as mock_advisory, \
             patch("weather.print_weather") as mock_print:
            weather.main()

        # validate_zip is called at least twice (DEFAULT_ZIP sanity check + arg validation)
        self.assertGreaterEqual(mock_validate.call_count, 2)
        mock_coords.assert_called_once()
        mock_weather.assert_called_once()
        mock_advisory.assert_called_once()
        mock_print.assert_called_once()

    # --- 2. With a zip arg → uses that zip ---

    def test_with_zip_arg_uses_provided_zip(self):
        """With a zip arg, main() prints 'Location: {zip}' for the provided zip."""
        stdout, _ = self._run_main(argv=["90210"])
        self.assertIn("Location: 90210", stdout)

    def test_with_zip_arg_different_from_default(self):
        """When a zip arg differs from DEFAULT_ZIP, the output location is the supplied zip."""
        from weather import DEFAULT_ZIP
        other_zip = "90210" if DEFAULT_ZIP != "90210" else "10002"
        stdout, _ = self._run_main(argv=[other_zip])
        self.assertIn(f"Location: {other_zip}", stdout)
        # DEFAULT_ZIP should NOT appear as the Location line
        lines = stdout.splitlines()
        location_lines = [l for l in lines if l.startswith("Location: ")]
        self.assertEqual(len(location_lines), 1)
        self.assertNotIn(f"Location: {DEFAULT_ZIP}", location_lines)

    # --- 3. Invalid zip → sys.exit(1), nothing to stdout ---

    def test_invalid_zip_exits_1(self):
        """An invalid zip code argument causes main() to exit with code 1."""
        with self.assertRaises(SystemExit) as ctx:
            self._run_main(argv=["ABCDE"])
        self.assertEqual(ctx.exception.code, 1)

    def test_invalid_zip_nothing_to_stdout(self):
        """An invalid zip code argument produces no output to stdout."""
        stdout_capture = StringIO()
        with patch("sys.argv", ["weather.py", "ABCDE"]), \
             patch("sys.stdout", stdout_capture), \
             patch("sys.stderr", StringIO()):
            try:
                import weather
                weather.main()
            except SystemExit:
                pass
        self.assertEqual(stdout_capture.getvalue(), "")

    def test_invalid_zip_writes_to_stderr(self):
        """An invalid zip code argument writes an error message to stderr."""
        stderr_capture = StringIO()
        with patch("sys.argv", ["weather.py", "123"]), \
             patch("sys.stdout", StringIO()), \
             patch("sys.stderr", stderr_capture):
            try:
                import weather
                weather.main()
            except SystemExit:
                pass
        self.assertIn("Error", stderr_capture.getvalue())

    # --- 4. DEFAULT_ZIP validated at startup (sanity check) ---

    def test_default_zip_validated_at_startup(self):
        """validate_zip is called with DEFAULT_ZIP before argument parsing (startup sanity check)."""
        import weather
        from weather import DEFAULT_ZIP

        call_order = []

        def recording_validate(zip_code):
            call_order.append(zip_code)
            return zip_code

        with patch("sys.argv", ["weather.py"]), \
             patch("sys.stdout", StringIO()), \
             patch("sys.stderr", StringIO()), \
             patch("weather.validate_zip", side_effect=recording_validate), \
             patch("weather.get_coordinates", return_value=(40.7484, -73.9967)), \
             patch("weather.get_weather", return_value=(72.5, 15)), \
             patch("weather.get_advisory", return_value=None), \
             patch("weather.print_weather"):
            weather.main()

        # The very first call to validate_zip must be with DEFAULT_ZIP
        self.assertTrue(len(call_order) >= 1, "validate_zip was never called")
        self.assertEqual(call_order[0], DEFAULT_ZIP,
                         f"First call to validate_zip should be DEFAULT_ZIP ({DEFAULT_ZIP!r}), "
                         f"got {call_order[0]!r}")

    # --- 5. Pipeline order: validate_zip → get_coordinates → get_weather → get_advisory → print_weather ---

    def test_pipeline_order(self):
        """Pipeline functions are called in the required order."""
        import weather

        call_order = []

        def recording_validate(zip_code):
            call_order.append(("validate_zip", zip_code))
            return zip_code

        def recording_coords(zip_code):
            call_order.append(("get_coordinates", zip_code))
            return (40.7484, -73.9967)

        def recording_weather(lat, lon):
            call_order.append(("get_weather", lat, lon))
            return (72.5, 15)

        def recording_advisory(lat, lon):
            call_order.append(("get_advisory", lat, lon))
            return None

        def recording_print(*args, **kwargs):
            call_order.append(("print_weather",) + args)

        with patch("sys.argv", ["weather.py", "10001"]), \
             patch("sys.stdout", StringIO()), \
             patch("sys.stderr", StringIO()), \
             patch("weather.validate_zip", side_effect=recording_validate), \
             patch("weather.get_coordinates", side_effect=recording_coords), \
             patch("weather.get_weather", side_effect=recording_weather), \
             patch("weather.get_advisory", side_effect=recording_advisory), \
             patch("weather.print_weather", side_effect=recording_print):
            weather.main()

        function_names = [entry[0] for entry in call_order]

        # validate_zip must appear before get_coordinates
        self.assertIn("validate_zip", function_names)
        self.assertIn("get_coordinates", function_names)
        self.assertIn("get_weather", function_names)
        self.assertIn("get_advisory", function_names)
        self.assertIn("print_weather", function_names)

        vi = function_names.index("validate_zip")
        ci = function_names.index("get_coordinates")
        wi = function_names.index("get_weather")
        ai = function_names.index("get_advisory")
        pi = function_names.index("print_weather")

        self.assertLess(vi, ci, "validate_zip must be called before get_coordinates")
        self.assertLess(ci, wi, "get_coordinates must be called before get_weather")
        self.assertLess(wi, ai, "get_weather must be called before get_advisory")
        self.assertLess(ai, pi, "get_advisory must be called before print_weather")


if __name__ == "__main__":
    unittest.main()

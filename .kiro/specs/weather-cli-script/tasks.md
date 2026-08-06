# Implementation Plan: Weather CLI Script

## Overview

Implement `weather.py` as a single-file Python script with `requirements.txt` and a property-based test suite in `tests/test_weather.py`. Tasks proceed from scaffolding → core logic → advisory feature → output → wiring, with property tests co-located with the code they validate.

---

## Tasks

- [x] 1. Scaffold project files and constants
  - Create `weather.py` with the `DEFAULT_ZIP` constant placed within the first 20 lines
  - Add the `requests` import guard (try/except ImportError → print to stderr + sys.exit(1))
  - Create `requirements.txt` with `requests>=2.28,<3`
  - Create `tests/` directory and an empty `tests/test_weather.py` with Hypothesis imports
  - _Requirements: 1.1, 6.1, 7.1_

- [x] 2. Implement zip code validation
  - [x] 2.1 Implement `validate_zip(zip_code: str) -> str`
    - Use `re.fullmatch(r"[0-9]{5}", zip_code)`; on failure print to stderr and call `sys.exit(1)`; on success return zip unchanged
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

  - [ ]* 2.2 Write property test for `validate_zip` — Property 2
    - **Property 2: Invalid zip codes are rejected**
    - Generate strings that do NOT match `[0-9]{5}` (wrong length, non-digit chars, empty, whitespace) and assert `validate_zip` exits non-zero and writes to stderr
    - Also generate valid 5-digit strings and assert they are returned unchanged
    - **Validates: Requirements 2.1, 2.2**

- [x] 3. Implement geocoding
  - [x] 3.1 Implement `get_coordinates(zip_code: str) -> tuple[float, float]`
    - Query `https://geocoding-api.open-meteo.com/v1/search` with params `name`, `count=1`, `language=en`, `format=json`, timeout=10s
    - On network error: print to stderr, sys.exit(1)
    - On zero results: print to stderr, sys.exit(1)
    - On malformed response (missing latitude/longitude): print descriptive error to stderr, sys.exit(1)
    - On success: return `(float(first["latitude"]), float(first["longitude"]))`
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 3.2 Write property test for `get_coordinates` — Property 3
    - **Property 3: Geocoding uses first result**
    - Mock the HTTP response with a list of N ≥ 1 result entries; assert the returned coordinates always match the first entry regardless of N
    - **Validates: Requirements 3.1**

  - [ ]* 3.3 Write property test for `get_coordinates` — Property 4
    - **Property 4: Malformed geocoding responses produce descriptive errors**
    - Generate response JSON with missing `results`, `latitude`, or `longitude` fields; assert sys.exit(1) is called and stderr contains a message
    - **Validates: Requirements 3.2, 3.3**

- [x] 4. Implement hour index resolution
  - [x] 4.1 Implement `find_current_hour_index(times: list[str]) -> int`
    - Pure function: find index of ISO 8601 entry matching current UTC hour (`%Y-%m-%dT%H:00`)
    - Fallback: match by hour-of-day if no exact date match; return 0 if no match found
    - _Requirements: 4.1_

  - [ ]* 4.2 Write property test for `find_current_hour_index` — Property 6
    - **Property 6: Hour index resolution is correct**
    - Generate lists that include an entry matching the current UTC hour at a random position; assert the returned index points to that entry
    - **Validates: Requirements 4.1**

- [x] 5. Implement weather data retrieval
  - [x] 5.1 Implement `get_weather(lat: float, lon: float) -> tuple[float, int]`
    - Query `https://api.open-meteo.com/v1/forecast` with `hourly=temperature_2m,precipitation_probability`, `temperature_unit=fahrenheit`, `forecast_days=1`, timeout=10s
    - On network error: print to stderr, sys.exit(1)
    - On missing `hourly`, `time`, `temperature_2m`, or `precipitation_probability` keys: print error naming the missing field to stderr, sys.exit(1)
    - On success: call `find_current_hour_index` and return `(float(temps[idx]), int(rain[idx]))`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 Write property test for `get_weather` — Property 5
    - **Property 5: Malformed weather responses produce descriptive errors**
    - Generate response JSON missing one of `hourly`, `time`, `temperature_2m`, `precipitation_probability`; assert sys.exit(1) is called and stderr names the missing field
    - **Validates: Requirements 4.3, 4.4**

- [x] 6. Checkpoint — core weather pipeline
  - Ensure `validate_zip`, `get_coordinates`, `find_current_hour_index`, and `get_weather` are implemented; run `python -m pytest tests/ -x` (or `python -m pytest tests/ --run`) and confirm all tests pass before continuing

- [x] 7. Implement weather advisories
  - [x] 7.1 Implement `get_advisory(lat: float, lon: float) -> dict | None`
    - Query `https://api.weather.gov/alerts/active?point={lat},{lon}` with `Accept: application/geo+json` header and timeout=10s
    - Parse `response.json()["features"]`; if empty list or key missing return `None`
    - Rank alerts by severity using order Extreme > Severe > Moderate > Minor > Unknown; on ties use first in response order
    - Extract `properties.event`, `properties.severity`, `properties.headline`, `properties.description[:500]` from the winning alert
    - Sanitize all text fields: replace/remove non-ASCII characters so every character is in U+0020–U+007E range
    - On network error: print a single warning line to stdout (not stderr), return `None` (non-fatal, no exit)
    - On unexpected response structure: print a single warning line to stdout, return `None` (non-fatal, no exit)
    - Return a dict `{"event": ..., "severity": ..., "headline": ..., "description": ...}` on success
    - _Requirements: 8.1, 8.2, 8.3, 8.5, 8.6, 8.7_

  - [ ]* 7.2 Write property test for `get_advisory` — Property 10
    - **Property 10: Advisory severity ordering is correct**
    - Generate lists of alerts with arbitrary severity strings (from the valid set); assert the returned advisory always has the highest-ranked severity; for ties assert response order is preserved
    - **Validates: Requirements 8.2**

  - [ ]* 7.3 Write property test for `get_advisory` — Property 11
    - **Property 11: Advisory ASCII sanitization removes/replaces non-ASCII chars**
    - Generate advisory text strings containing arbitrary Unicode; assert every character in all dict values returned by `get_advisory` is within U+0020–U+007E
    - **Validates: Requirements 8.7**

  - [ ]* 7.4 Write property test for `get_advisory` — Property 12
    - **Property 12: Advisory failure is non-fatal**
    - Simulate network errors and malformed responses; assert `get_advisory` returns `None` without calling `sys.exit`, and that a warning line is printed to stdout
    - **Validates: Requirements 8.5, 8.6**

- [x] 8. Implement output formatting
  - [x] 8.1 Implement `print_weather(zip_code: str, temp: float, rain: int, advisory: dict | None = None) -> None`
    - Always print: `"Location: {zip_code}"`, `"Temperature: {temp:.1f}degF"`, `"Chance of Rain: {rain}%"`
    - If `advisory` is a dict: print `"Advisory Event: {event}"`, `"Advisory Severity: {severity}"`, `"Advisory Headline: {headline}"`, `"Advisory Description: {description}"` (description already truncated to 500 chars by `get_advisory`)
    - If `advisory` is `None`: print `"Advisory: No active advisories"`
    - Note: the sentinel value `"FETCH_FAILED"` is not needed — callers pass `None` for both "no alerts" and "fetch failed"; the warning line is already printed inside `get_advisory`. If distinguishing the two cases in output is desired, use a sentinel string or a second parameter.
    - All characters in output must be printable ASCII (U+0020–U+007E); advisory text is already sanitized by `get_advisory`
    - _Requirements: 5.1, 5.2, 5.3, 8.3, 8.4, 8.7_

  - [ ]* 8.2 Write property test for `print_weather` — Property 7
    - **Property 7: Output format is three (or more) labeled lines**
    - For any valid zip, temp, and rain, assert stdout lines start with the exact labels `"Location: "`, `"Temperature: "`, `"Chance of Rain: "`
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 8.3 Write property test for `print_weather` — Property 8
    - **Property 8: Output is printable ASCII only**
    - For any valid inputs including advisory dicts with sanitized text, assert every character in combined stdout output has ordinal in 0x20–0x7E range
    - **Validates: Requirements 5.3, 8.7**

- [x] 9. Implement `main()` and wire everything together
  - [x] 9.1 Implement `main() -> None`
    - Call `validate_zip(DEFAULT_ZIP)` at startup as a fail-fast sanity check
    - Build `argparse.ArgumentParser` with descriptive help; add optional positional `zip_code` arg defaulting to `DEFAULT_ZIP`
    - Call `validate_zip(args.zip_code)` → `get_coordinates(zip_code)` → `get_weather(lat, lon)` → `get_advisory(lat, lon)` → `print_weather(zip_code, temp, rain, advisory)`
    - Guard with `if __name__ == "__main__": main()`
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 4.1, 8.1_

  - [ ]* 9.2 Write property test for `main` — Property 1
    - **Property 1: CLI argument overrides DEFAULT_ZIP**
    - Patch `get_coordinates`, `get_weather`, and `get_advisory` with fixed return values; generate valid 5-digit zip codes different from `DEFAULT_ZIP`; invoke `main()` with that zip as sys.argv; assert `"Location: {zip}"` appears in stdout
    - **Validates: Requirements 1.2, 2.1**

  - [ ]* 9.3 Write property test for `main` — Property 9
    - **Property 9: No stdout output on failure**
    - Simulate each fatal error condition (network failure, empty geocoding result, malformed response); assert stdout is empty and sys.exit is called with non-zero code
    - **Validates: Requirements 3.2, 3.3, 4.3, 4.4, 5.3_

- [x] 10. Final checkpoint — full suite
  - Run `python -m pytest tests/ -x` and confirm all tests pass
  - Manually verify `python weather.py` prints the expected labeled lines including the advisory section
  - Ensure all characters in output are printable ASCII
  - Ask the user if any questions arise

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- The `get_advisory` failure path prints a warning to **stdout** (not stderr) and returns `None` — the script does not exit
- `print_weather` must distinguish between "no alerts" (`None` + no prior warning) and "fetch failed" (caller passes a distinct sentinel or a separate flag); the simplest approach is to have `get_advisory` return a special sentinel string on failure and `None` on "no alerts", then check for that in `print_weather`
- Advisory description is capped at 500 characters inside `get_advisory` before sanitization
- All property tests use [Hypothesis](https://hypothesis.readthedocs.io/); install via `pip install hypothesis` for test runs
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1"] },
    { "id": 1, "tasks": ["2.2", "3.1", "4.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "4.2", "5.1"] },
    { "id": 3, "tasks": ["5.2", "7.1"] },
    { "id": 4, "tasks": ["7.2", "7.3", "7.4", "8.1"] },
    { "id": 5, "tasks": ["8.2", "8.3", "9.1"] },
    { "id": 6, "tasks": ["9.2", "9.3"] }
  ]
}
```

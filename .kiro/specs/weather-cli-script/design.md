# Design Document

## Overview

`weather.py` is a single-file Python script that fetches the current temperature and chance of rain for a US zip code. It performs two HTTP requests in sequence: first to the Open-Meteo geocoding API to convert a zip code into a latitude/longitude pair, then to the Open-Meteo forecast API to retrieve hourly weather data. The result is printed as three plain-text lines to stdout.

The script is intentionally minimal — no external frameworks, no local storage, no concurrency. All logic lives in one file and is callable from the command line on any Python 3.8+ platform.

---

## Architecture

```
weather.py
├── Constants
│   └── DEFAULT_ZIP  (module-level string, within first 20 lines)
├── Validation
│   └── validate_zip(zip_code: str) -> str   # returns zip or exits
├── Geocoding
│   └── get_coordinates(zip_code: str) -> tuple[float, float]
├── Weather Retrieval
│   └── get_weather(lat: float, lon: float) -> tuple[float, int]
├── Hour Index Resolution
│   └── find_current_hour_index(times: list[str]) -> int
├── Output
│   └── print_weather(zip_code: str, temp: float, rain: int) -> None
└── Entry Point
    └── main() -> None
```

Each function has a single responsibility and raises no exceptions that reach the top level — errors are caught, written to stderr, and `sys.exit(1)` is called.

---

## Components

### Constants

```python
DEFAULT_ZIP = "10001"  # New York, NY — within first 20 lines
```

`DEFAULT_ZIP` is a module-level string constant. It must match `[0-9]{5}`. The script validates it at startup before doing anything else.

---

### Dependency Import Guard

The `requests` import is wrapped in a try/except at the top of the file:

```python
try:
    import requests
except ImportError:
    import sys
    print(
        "Error: Required package 'requests' not found. "
        "Run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)
```

This runs before any function is called, ensuring a clear error on missing dependency.

---

### `validate_zip(zip_code: str) -> str`

Validates that a zip code string matches `[0-9]{5}`. On failure, prints to stderr and calls `sys.exit(1)`. On success, returns the zip code unchanged.

```python
import re
import sys

def validate_zip(zip_code: str) -> str:
    if not re.fullmatch(r"[0-9]{5}", zip_code):
        print(f"Error: Invalid zip code '{zip_code}'. Must be exactly 5 digits.", file=sys.stderr)
        sys.exit(1)
    return zip_code
```

---

### `get_coordinates(zip_code: str) -> tuple[float, float]`

Queries `https://geocoding-api.open-meteo.com/v1/search?name={zip}&count=1&language=en&format=json`.

- On network error: prints `"Error: Failed to reach geocoding service — {error}"` to stderr, exits 1.
- On empty results: prints `"Error: No location found for zip code {zip}"` to stderr, exits 1.
- On missing/malformed fields: prints a descriptive error to stderr, exits 1.
- On success: returns `(latitude, longitude)` from the first result.

```python
def get_coordinates(zip_code: str) -> tuple:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": zip_code, "count": 1, "language": "en", "format": "json"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to reach geocoding service — {e}", file=sys.stderr)
        sys.exit(1)

    results = data.get("results")
    if not results:
        print(f"Error: No location found for zip code {zip_code}", file=sys.stderr)
        sys.exit(1)

    first = results[0]
    try:
        return float(first["latitude"]), float(first["longitude"])
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error: Unexpected geocoding response format — {e}", file=sys.stderr)
        sys.exit(1)
```

---

### `find_current_hour_index(times: list) -> int`

A pure function that finds the index of the entry in `times` whose hour matches the current UTC hour. The `times` list contains ISO 8601 strings like `"2024-07-15T14:00"`.

```python
from datetime import datetime, timezone

def find_current_hour_index(times: list) -> int:
    current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    current_str = current_hour.strftime("%Y-%m-%dT%H:00")
    for i, t in enumerate(times):
        if t == current_str:
            return i
    # Fallback: match by hour of day if date differs
    current_h = current_hour.hour
    for i, t in enumerate(times):
        try:
            if datetime.fromisoformat(t).hour == current_h:
                return i
        except ValueError:
            continue
    return 0
```

---

### `get_weather(lat: float, lon: float) -> tuple[float, int]`

Queries `https://api.open-meteo.com/v1/forecast` with `hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit`.

- On network error: prints `"Error: Failed to reach weather service — {error}"` to stderr, exits 1.
- On missing fields: prints `"Error: Unexpected response format — missing field {field}"` to stderr, exits 1.
- On success: returns `(temperature_fahrenheit, precipitation_probability_percent)` for the current hour.

```python
def get_weather(lat: float, lon: float) -> tuple:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "temperature_unit": "fahrenheit",
        "forecast_days": 1,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to reach weather service — {e}", file=sys.stderr)
        sys.exit(1)

    try:
        hourly = data["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        rain = hourly["precipitation_probability"]
    except KeyError as e:
        print(f"Error: Unexpected response format — missing field {e}", file=sys.stderr)
        sys.exit(1)

    idx = find_current_hour_index(times)
    return float(temps[idx]), int(rain[idx])
```

---

### `print_weather(zip_code: str, temp: float, rain: int) -> None`

Formats and writes the three output lines to stdout. Uses only printable ASCII characters.

```python
def print_weather(zip_code: str, temp: float, rain: int) -> None:
    print(f"Location: {zip_code}")
    print(f"Temperature: {temp:.1f}degF")
    print(f"Chance of Rain: {rain}%")
```

> Note: The degree sign `°` (U+00B0) is outside printable ASCII (U+0020–U+007E). The output uses the ASCII-safe literal `degF` instead to satisfy Requirement 5.2.

---

### `main() -> None`

The entry point. Parses arguments, validates, orchestrates the two API calls, and prints output.

```python
import argparse

def main() -> None:
    validate_zip(DEFAULT_ZIP)  # Fail fast if the constant is misconfigured

    parser = argparse.ArgumentParser(
        description="Fetch current temperature and chance of rain for a US zip code."
    )
    parser.add_argument(
        "zip_code",
        nargs="?",
        default=DEFAULT_ZIP,
        help="US zip code (5 digits). Defaults to DEFAULT_ZIP if omitted.",
    )
    args = parser.parse_args()

    zip_code = validate_zip(args.zip_code)
    lat, lon = get_coordinates(zip_code)
    temp, rain = get_weather(lat, lon)
    print_weather(zip_code, temp, rain)


if __name__ == "__main__":
    main()
```

---

## Data Models

No persistent data models. All data is in-memory and transient.

| Name | Type | Description |
|------|------|-------------|
| `zip_code` | `str` | Validated 5-digit string |
| `lat`, `lon` | `float` | WGS84 coordinates from geocoding |
| `temp` | `float` | Temperature in °F for current hour |
| `rain` | `int` | Precipitation probability % for current hour |
| `times` | `list[str]` | ISO 8601 hourly timestamps from Weather_API |
| `idx` | `int` | Index into `times` for the current UTC hour |

---

## Error Handling

All errors follow a single pattern: print a human-readable message to `stderr`, then call `sys.exit(1)`. No exceptions propagate to the top level.

| Condition | stderr Message | Exit Code |
|-----------|---------------|-----------|
| `requests` not installed | `Error: Required package 'requests' not found. Run: pip install -r requirements.txt` | 1 |
| Invalid zip code format | `Error: Invalid zip code '{zip}'. Must be exactly 5 digits.` | 1 |
| Network error (geocoding) | `Error: Failed to reach geocoding service — {error}` | 1 |
| No geocoding results | `Error: No location found for zip code {zip}` | 1 |
| Malformed geocoding response | `Error: Unexpected geocoding response format — {error}` | 1 |
| Network error (weather) | `Error: Failed to reach weather service — {error}` | 1 |
| Missing weather fields | `Error: Unexpected response format — missing field {field}` | 1 |

On any error, stdout is empty.

---

## External Interfaces

### Geocoding API

- **URL**: `https://geocoding-api.open-meteo.com/v1/search`
- **Method**: GET
- **Key params**: `name={zip}`, `count=1`, `language=en`, `format=json`
- **Timeout**: 10 seconds
- **Expected response shape**:
  ```json
  {
    "results": [
      { "latitude": 40.7484, "longitude": -73.9967, "name": "New York City", ... }
    ]
  }
  ```

### Weather Forecast API

- **URL**: `https://api.open-meteo.com/v1/forecast`
- **Method**: GET
- **Key params**: `latitude`, `longitude`, `hourly=temperature_2m,precipitation_probability`, `temperature_unit=fahrenheit`, `forecast_days=1`
- **Timeout**: 10 seconds
- **Expected response shape**:
  ```json
  {
    "hourly": {
      "time": ["2024-07-15T00:00", "2024-07-15T01:00", ...],
      "temperature_2m": [72.1, 71.3, ...],
      "precipitation_probability": [5, 10, ...]
    }
  }
  ```

---

## Dependency Declaration

`requirements.txt`:
```
requests>=2.28,<3
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: CLI argument overrides default zip

*For any* valid 5-digit zip code supplied as a CLI argument, the `Location:` line printed to stdout should display that zip code rather than `DEFAULT_ZIP`.

**Validates: Requirements 1.4, 2.1**

---

### Property 2: Invalid zip codes are rejected

*For any* string that does not match `[0-9]{5}` (wrong length, non-digit characters, empty string, whitespace), `validate_zip` should return a non-zero exit and write a message to stderr.

**Validates: Requirements 2.4, 2.5**

---

### Property 3: Geocoding uses first result

*For any* mock geocoding response containing one or more result entries, `get_coordinates` should return the latitude and longitude from the first entry, regardless of how many entries are present.

**Validates: Requirements 3.2**

---

### Property 4: Malformed geocoding responses produce descriptive errors

*For any* geocoding response JSON that is missing `results`, `latitude`, or `longitude` fields, `get_coordinates` should call `sys.exit(1)` and write a descriptive message to stderr.

**Validates: Requirements 3.5**

---

### Property 5: Malformed weather responses produce descriptive errors

*For any* weather API response JSON that is missing the `hourly` key, `time` array, `temperature_2m` array, or `precipitation_probability` array, `get_weather` should call `sys.exit(1)` and write a message to stderr naming the missing field.

**Validates: Requirements 4.4**

---

### Property 6: Hour index resolution is correct

*For any* list of ISO 8601 hourly timestamps that contains an entry matching the current UTC hour, `find_current_hour_index` should return the index of that matching entry.

**Validates: Requirements 4.5**

---

### Property 7: Output format is three labeled lines

*For any* valid zip code, temperature value, and rain percentage, `print_weather` should produce output whose lines are exactly `"Location: {zip}"`, `"Temperature: {value}degF"`, and `"Chance of Rain: {value}%"`.

**Validates: Requirements 5.1**

---

### Property 8: Output is printable ASCII only

*For any* valid zip code, temperature, and rain percentage passed to `print_weather`, every character in the combined stdout output should have an ordinal value in the range U+0020–U+007E.

**Validates: Requirements 5.2**

---

### Property 9: No stdout output on failure

*For any* error condition (network failure, invalid zip, empty geocoding result, malformed API response), the script should produce no output to stdout and write only to stderr before exiting with a non-zero code.

**Validates: Requirements 5.3**

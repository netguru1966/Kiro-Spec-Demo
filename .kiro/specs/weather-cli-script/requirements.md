# Requirements Document

## Introduction

A cross-platform Python terminal script that fetches the current temperature and chance of rain for a given US zip code. The script uses the Open-Meteo API (free, no API key required) with a geocoding step to convert a zip code to latitude/longitude before retrieving weather data. A default zip code is stored as a constant near the top of the script and can be overridden via a CLI argument. Output is clean, readable plain-text formatted for terminal display on macOS, Windows, and Linux.

## Glossary

- **Script**: The single Python file (`weather.py`) that implements all functionality.
- **Default_Zip**: The constant defined near the top of the Script holding the fallback zip code when no CLI argument is provided.
- **CLI_Argument**: The optional positional or flag argument supplied by the user when invoking the Script from the terminal.
- **Geocoding_Service**: The external service used to resolve a zip code to a latitude/longitude coordinate pair. The Script uses the Open-Meteo geocoding API (`geocoding-api.open-meteo.com`).
- **Weather_API**: The Open-Meteo forecast API (`api.open-meteo.com`) that returns current weather data given latitude and longitude.
- **Current_Temperature**: The temperature value for the current hour returned by the Weather_API, expressed in degrees Fahrenheit.
- **Chance_of_Rain**: The precipitation probability percentage for the current hour returned by the Weather_API.
- **Terminal_Output**: The plain-text lines written to stdout by the Script.
- **NWS_Alerts_API**: The National Weather Service REST API (`api.weather.gov`) used to retrieve active weather alerts for a geographic point.
- **Advisory**: The highest-severity active NWS weather alert for the current location, if any.
- **Advisory_Severity**: The NWS severity classification of an alert (Extreme, Severe, Moderate, Minor, Unknown), used to select the single alert to display when multiple are active.

---

## Requirements

### Requirement 1: Default Zip Code Constant

**User Story:** As a developer, I want a clearly located default zip code constant in the script, so that I can change the default without searching through the code.

#### Acceptance Criteria

1. THE Script SHALL define `DEFAULT_ZIP` as a module-level string constant placed within the first 20 lines of the file.
2. THE Script SHALL enforce the 20-line placement rule for `DEFAULT_ZIP` regardless of any imports, comments, or docstrings that precede it; if `DEFAULT_ZIP` appears on line 21 or later the requirement is violated.
3. THE Script SHALL use `DEFAULT_ZIP` as the zip code when no CLI_Argument is provided.

---

### Requirement 2: CLI Argument Override

**User Story:** As a user, I want to supply a zip code on the command line, so that I can check weather for any location without editing the script.

#### Acceptance Criteria

1. WHEN the Script is invoked with a positional argument, THE Script SHALL use that argument as the zip code instead of `DEFAULT_ZIP`.
2. WHEN the Script is invoked with no positional argument, THE Script SHALL use `DEFAULT_ZIP` as the zip code.
3. THE Script SHALL accept the zip code argument via Python's `argparse` module with a descriptive help string.

---

### Requirement 3: Zip Code to Coordinates Resolution

**User Story:** As a user, I want the script to automatically convert my zip code to geographic coordinates, so that I do not need to know the latitude and longitude manually.

#### Acceptance Criteria

1. WHEN a zip code is provided, THE Script SHALL query the Geocoding_Service to resolve the zip code to a latitude and longitude.
2. IF the Geocoding_Service returns zero results for the supplied zip code, THEN THE Script SHALL print a descriptive error message to stderr and exit with exit code 1.
3. IF the Geocoding_Service request fails due to a network error, THEN THE Script SHALL print a descriptive error message to stderr and exit with exit code 1.
4. THE Script SHALL use the same exit code (1) and the same error message format pattern for both zero-results and network-error failure modes, so the user receives a consistent failure signal regardless of the underlying cause.

---

### Requirement 4: Weather Data Retrieval

**User Story:** As a user, I want the script to fetch current weather data from Open-Meteo, so that I receive up-to-date conditions without needing an API key.

#### Acceptance Criteria

1. WHEN valid coordinates are obtained, THE Script SHALL query the Weather_API for `temperature_2m` and `precipitation_probability` at the current hour using the `hourly` endpoint.
2. THE Script SHALL request temperature data in Fahrenheit by passing `temperature_unit=fahrenheit` to the Weather_API.
3. IF the Weather_API request fails due to a network error, THEN THE Script SHALL print a descriptive error message to stderr and exit with a non-zero exit code.
4. IF the Weather_API response does not contain the expected fields, THEN THE Script SHALL print a descriptive error message to stderr and exit with a non-zero exit code.
5. THE Script SHALL NOT retry the Weather_API request under any condition, including network errors and missing response fields; each invocation makes exactly one Weather_API request and fails fast on any error.

> **Note (scope):** The Script is only required to implement error handling as specified in these criteria. Bugs within the Script's own error-handling code are outside the scope of these requirements.

---

### Requirement 5: Terminal Output

**User Story:** As a user, I want clean, readable output in my terminal, so that I can quickly understand the current conditions for my location.

#### Acceptance Criteria

1. WHEN weather data is successfully retrieved, THE Script SHALL print the zip code, Current_Temperature (in °F), and Chance_of_Rain (as a percentage) to stdout.
2. THE Script SHALL format Terminal_Output as human-readable labeled lines (e.g., `Location: 90210`, `Temperature: 72°F`, `Chance of Rain: 15%`).
3. THE Script SHALL produce Terminal_Output using only printable ASCII characters to ensure compatibility across macOS, Windows, and Linux terminals.

---

### Requirement 6: Cross-Platform Compatibility

**User Story:** As a developer, I want the script to run without modification on macOS, Windows, and Linux, so that all team members can use it regardless of their operating system.

#### Acceptance Criteria

1. THE Script SHALL use only Python standard library modules and the `requests` third-party package, with no platform-specific dependencies.
2. THE Script SHALL be executable via `python weather.py` on macOS, Linux, and Windows without requiring environment-specific configuration.
3. THE Script SHALL use `sys.exit()` for process termination rather than OS-specific exit mechanisms.

---

### Requirement 7: Dependency Declaration

**User Story:** As a developer, I want the script's dependencies declared in a standard file, so that I can install them reliably in any environment.

#### Acceptance Criteria

1. THE Script's repository SHALL include a `requirements.txt` file listing `requests` with a pinned major version (e.g., `requests>=2.28,<3`).

---

### Requirement 8: Weather Advisories

**User Story:** As a user, I want to see active weather advisories for my location, so that I am aware of dangerous or significant weather conditions beyond temperature and rain.

#### Acceptance Criteria

1. WHEN valid coordinates are obtained, THE Script SHALL query the NWS_Alerts_API at `https://api.weather.gov/alerts/active?point={lat},{lon}` to retrieve active weather alerts for the current location.
2. WHEN the NWS_Alerts_API returns multiple active alerts, THE Script SHALL select the single alert with the highest Advisory_Severity using the precedence order Extreme > Severe > Moderate > Minor > Unknown.
3. WHEN the NWS_Alerts_API returns active alerts, THE Script SHALL display the selected Advisory's event name, Advisory_Severity, headline, and full description text as part of Terminal_Output.
4. WHEN the NWS_Alerts_API returns no active alerts, THE Script SHALL display the line `Advisory: No active advisories` as part of Terminal_Output.
5. IF the NWS_Alerts_API request fails due to a network error, THEN THE Script SHALL print a warning line to stdout and continue displaying the temperature and rain output without exiting.
6. IF the NWS_Alerts_API response does not contain the expected fields, THEN THE Script SHALL print a warning line to stdout and continue displaying the temperature and rain output without exiting.
7. THE Script SHALL render all advisory text using only printable ASCII characters, replacing or removing any non-ASCII characters before writing to Terminal_Output.

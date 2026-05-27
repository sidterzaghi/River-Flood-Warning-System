# Product Requirements Document (PRD)
## Automated River Water Level Warning System via WhatsApp
### Sourced from DHM Nepal (dhm.gov.np)

**Version:** 2.0  
**Status:** Ready for Implementation  
**Audience:** Coding agents, backend developers  
**Data Source:** Department of Hydrology and Meteorology, Nepal — https://dhm.gov.np/hydrology/river-watch

---

## 1. Overview

### What This System Does

A Python backend daemon that:
1. Lets the operator configure which rivers/stations to monitor, custom warning thresholds, and a list of recipient WhatsApp numbers — all through a config file or interactive CLI setup
2. Periodically scrapes live river water level telemetry from the DHM River Watch page
3. Evaluates each monitored station's water level against the operator's custom threshold (or DHM's published warning/danger levels)
4. Broadcasts emergency WhatsApp alerts to all configured recipients when a threshold is breached

### What This System Does NOT Do

- No web UI or dashboard (config only, CLI or file-based)
- No database persistence (stateless per run; state held in config file)
- No SMS, email, or other notification channels (WhatsApp only)
- No historical data graphing

---

## 2. Data Source Specification

**URL:** `https://dhm.gov.np/hydrology/river-watch`  
**Operator:** Department of Hydrology and Meteorology (DHM), Government of Nepal  
**Rendering:** JavaScript-rendered (React/dynamic). Requires Playwright or Selenium — `requests` + `BeautifulSoup` alone will not work on this page.

### Available Data Fields Per Station

| Field | Description | Example |
|---|---|---|
| `station_no` | Unique station identifier | `501` |
| `basin_name` | River basin name | `Bagmati` |
| `station_name` | Full station name | `Bagmati River at Gaurighat` |
| `district_name` | District where station is located | `Kathmandu` |
| `water_level_m` | Current live water level in meters | `3.45` |
| `warning_level_m` | DHM-published warning threshold in meters | `5.0` |
| `danger_level_m` | DHM-published danger threshold in meters | `6.8` |
| `trend` | Current direction of water level change | `Rising` / `Falling` / `Steady` |
| `status` | DHM classification of current condition | `Below Warning Level` / `Above Warning Level` / `Above Danger Level` |

### Scraping Approach

Since the River Watch page is JavaScript-rendered, use **Playwright** (preferred) or **Selenium**:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://dhm.gov.np/hydrology/river-watch")
    page.wait_for_selector("table tbody tr")  # Wait for data to load
    html = page.content()
    browser.close()
    # Parse html with BeautifulSoup
```

**Alternative:** Investigate whether the page calls an internal JSON API endpoint (inspect browser Network tab for XHR/fetch calls to `/api/` or similar). If a JSON API exists, use `requests` directly — this is faster and more stable than browser automation.

> **TODO for implementer:** Open `https://dhm.gov.np/hydrology/river-watch` in browser DevTools → Network tab → filter XHR — check if there is a direct API call returning station data as JSON. If found, document the endpoint and use `requests` instead of Playwright.

---

## 3. System Architecture

The system runs as a sequential pipeline, triggered on a schedule:

```
[ User Configuration Layer ]
           ↓
   (on startup / config load)
           ↓
[ Data Extraction Layer ]  ←── dhm.gov.np/hydrology/river-watch
           ↓
[ Filter: monitored stations only ]
           ↓
[ Analytical & Rules Engine ]
           ↓
[ Notification Gateway ]  ──→  WhatsApp (all configured recipients)
```

All configuration (rivers, thresholds, recipients) is loaded from a persistent config file at startup. No configuration is hardcoded in the program logic.

---

## 4. Component Specifications

---

### 4.1 User Configuration Layer

**Responsibility:** Load, display, and allow editing of all operator-defined settings. This is the entry point for setup.

**Config is stored in:** `config.json` (persistent across runs)

#### 4.1.1 Config File Schema

```json
{
  "monitored_stations": [
    {
      "station_name": "Bagmati River at Gaurighat",
      "station_no": "501",
      "custom_warning_level_m": 4.5,
      "use_dhm_warning_level": false
    },
    {
      "station_name": "Karnali at Chisapani",
      "station_no": "210",
      "custom_warning_level_m": null,
      "use_dhm_warning_level": true
    }
  ],
  "whatsapp_recipients": [
    "+9779800000001",
    "+9779800000002",
    "+9779800000003"
  ],
  "check_interval_minutes": 15,
  "whatsapp_api_provider": "twilio",
  "alert_cooldown_minutes": 60
}
```

#### 4.1.2 Config Fields Reference

| Field | Type | Description |
|---|---|---|
| `monitored_stations` | list | One entry per river station to monitor |
| `station_name` | string | Must match the DHM station name exactly |
| `station_no` | string | DHM station number (used as unique key) |
| `custom_warning_level_m` | float or null | Operator-defined threshold in meters. Set to `null` to use DHM level |
| `use_dhm_warning_level` | bool | If `true`, use DHM's published `warning_level_m`; ignore `custom_warning_level_m` |
| `whatsapp_recipients` | list of strings | All phone numbers to receive alerts. E.164 format (e.g. `+9779800000001`) |
| `check_interval_minutes` | int | How often the daemon runs (used by cron or scheduler) |
| `whatsapp_api_provider` | string | `"twilio"` or `"meta"` |
| `alert_cooldown_minutes` | int | Minimum gap between repeated alerts for the same station (prevents alert spam) |

#### 4.1.3 Interactive CLI Setup (Optional but Recommended)

Provide a `setup.py` script that walks the operator through configuration without editing JSON manually:

```
$ python setup.py

=== River Warning System Setup ===

[1] Add a river station to monitor
[2] Remove a station
[3] Set custom warning level for a station
[4] Add a WhatsApp recipient number
[5] Remove a recipient number
[6] View current configuration
[7] Save and exit
```

**Station selection flow:**
1. Fetch full station list from DHM River Watch page on startup
2. Display filterable list (by basin, district, or station name)
3. Operator selects station → system stores `station_name` and `station_no`
4. Prompt: "Use DHM's published warning level (X.X m)? [Y/n]"
5. If N → prompt for custom threshold in meters

**Recipient management flow:**
1. Prompt for phone number in E.164 format
2. Validate format with regex: `^\+\d{10,15}$`
3. Add to `whatsapp_recipients` list
4. Confirm: "Number added. Current recipients: [list]"

---

### 4.2 Data Extraction Layer (Scraper)

**Responsibility:** Fetch the live River Watch table from DHM and return all station records as structured data.

**Input:** None  
**Output:** `list[dict]` — one dict per station row, with all fields from Section 2

**Stub signature:**
```python
def scrape_river_watch() -> list[dict]:
    """
    Returns a list of station dicts, e.g.:
    [
      {
        "station_no": "501",
        "station_name": "Bagmati River at Gaurighat",
        "basin_name": "Bagmati",
        "district_name": "Kathmandu",
        "water_level_m": 3.45,
        "warning_level_m": 5.0,
        "danger_level_m": 6.8,
        "trend": "Rising",
        "status": "Below Warning Level"
      },
      ...
    ]
    """
```

**Implementation Requirements:**
- Use Playwright (headless Chromium) to render the page, then parse with BeautifulSoup
- Wait for the table to be populated before reading HTML (`page.wait_for_selector("table tbody tr")`)
- Parse `water_level_m`, `warning_level_m`, `danger_level_m` as `float` (strip units, handle `--` or missing values as `None`)
- Handle network timeouts: retry up to 3 times with 10-second delays before failing the cycle
- On total failure: log the error, do NOT send a false alert, exit gracefully

---

### 4.3 Station Filter

**Responsibility:** From the full scraped list, return only the stations the operator has configured for monitoring.

**Input:** `all_stations: list[dict]`, `config: dict`  
**Output:** `list[dict]` — only the monitored stations, with config data merged in

```python
def filter_monitored_stations(all_stations: list[dict], config: dict) -> list[dict]:
    """
    Match by station_no. Merge config fields (custom threshold, use_dhm_level) 
    into each returned station dict.
    """
```

---

### 4.4 Analytical & Rules Engine

**Responsibility:** For each monitored station, determine the effective warning threshold and evaluate whether an alert should fire.

**Input:** `station: dict` (merged station + config data)  
**Output:** `dict` with keys `should_alert: bool`, `effective_threshold_m: float`, `reason: str`

**Threshold resolution logic:**
```
if station["use_dhm_warning_level"]:
    effective_threshold = station["warning_level_m"]   # from DHM scrape
else:
    effective_threshold = station["custom_warning_level_m"]  # from config

if station["water_level_m"] >= effective_threshold:
    should_alert = True
```

**Alert cooldown logic:**
- Track last alert time per station in a runtime state dict (in-memory)
- If `(now - last_alert_time) < alert_cooldown_minutes`, suppress the alert even if threshold is breached
- Reset cooldown timer when water level drops back below threshold

**Stub signature:**
```python
def evaluate_station(station: dict, last_alert_times: dict) -> dict:
    """
    Returns:
    {
      "should_alert": True,
      "effective_threshold_m": 4.5,
      "reason": "Water level 5.2m exceeds custom threshold 4.5m (Trend: Rising)"
    }
    """
```

---

### 4.5 Notification Gateway (WhatsApp)

**Responsibility:** Send an alert message to ALL configured recipient numbers.

**Input:** `station: dict`, `evaluation: dict`, `recipients: list[str]`  
**Output:** None (side effect: HTTP POST per recipient)

**Message format:**
```
⚠️ FLOOD WARNING — Bagmati River at Gaurighat
📍 District: Kathmandu | Basin: Bagmati
💧 Current Level: 5.20 m
🚨 Threshold: 4.50 m (Custom)
📈 Trend: Rising
🕐 Time: 2026-05-25 14:30 NPT
Source: DHM Nepal (dhm.gov.np)
```

**Sending behavior:**
- Iterate over all numbers in `whatsapp_recipients`
- Send independently to each number — a failure for one number must not block others
- Log success/failure per recipient

**Supported API providers (choose one via config):**

| Provider | Base URL | Notes |
|---|---|---|
| Twilio WhatsApp | `https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json` | Easier setup; requires Twilio account + WhatsApp sandbox or approved number |
| Meta Cloud API | `https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages` | Official; requires Meta Business account + verified number |

**Stub signature:**
```python
def dispatch_alerts(station: dict, evaluation: dict, recipients: list[str]) -> None:
    """
    Sends alert to all recipients. Logs each outcome.
    Raises no exceptions — errors are caught and logged per recipient.
    """
```

**TODO for implementer:**
- Select provider and implement the HTTP POST body format for that provider
- Store all credentials in `.env` (see Section 5)
- Test with at least 2 recipient numbers to validate multi-send logic

---

### 4.6 Main Orchestration Loop

**Responsibility:** Load config, run the full pipeline, log outcomes.

```python
def main():
    config = load_config("config.json")
    last_alert_times = {}  # { station_no: datetime }

    print(f"[{now()}] Starting river watch cycle for {len(config['monitored_stations'])} stations...")

    try:
        all_stations = scrape_river_watch()
        monitored = filter_monitored_stations(all_stations, config)

        for station in monitored:
            evaluation = evaluate_station(station, last_alert_times)

            if evaluation["should_alert"]:
                dispatch_alerts(station, evaluation, config["whatsapp_recipients"])
                last_alert_times[station["station_no"]] = datetime.now()
                print(f"[ALERT SENT] {station['station_name']} — {evaluation['reason']}")
            else:
                print(f"[OK] {station['station_name']} — Level: {station['water_level_m']}m — No alert")

    except Exception as e:
        print(f"[FATAL ERROR] Cycle failed: {e}")

if __name__ == "__main__":
    main()
```

---

## 5. Environment Variables (`.env`)

All secrets go in `.env`. Never commit this file to version control.

| Variable | Required | Description |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | If using Twilio | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | If using Twilio | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | If using Twilio | Sender number, e.g. `whatsapp:+14155238886` |
| `META_ACCESS_TOKEN` | If using Meta | Meta Graph API access token |
| `META_PHONE_NUMBER_ID` | If using Meta | Meta WhatsApp phone number ID |

---

## 6. Recommended File Structure

```
river_warning_system/
├── main.py                  # Orchestration loop — entry point
├── setup.py                 # Interactive CLI for configuration
├── scraper.py               # DHM River Watch scraper (Playwright)
├── analyzer.py              # Rules engine — threshold evaluation
├── notifier.py              # WhatsApp dispatch (Twilio or Meta)
├── config_manager.py        # Load/save/validate config.json
├── config.json              # Operator configuration (committed without secrets)
├── .env                     # API secrets (NEVER commit)
├── .env.example             # Template showing required env vars
├── requirements.txt
└── README.md
```

---

## 7. Dependencies

```
playwright>=1.40.0          # Browser automation for JS-rendered DHM page
beautifulsoup4>=4.12.0      # HTML parsing after Playwright renders page
requests>=2.31.0            # HTTP calls to WhatsApp API
python-dotenv>=1.0.0        # Load .env secrets
twilio>=8.0.0               # Only if using Twilio provider
```

**Post-install step for Playwright:**
```bash
pip install playwright --break-system-packages
playwright install chromium
```

---

## 8. Deployment

### Option A — VPS with Cron (Recommended for simplicity)

```bash
# Run every 15 minutes
*/15 * * * * /usr/bin/python3 /home/user/river_warning/main.py >> /var/log/river_warning.log 2>&1
```

Providers: AWS EC2 t2.micro, DigitalOcean Droplet, Hetzner Cloud (~$4–6/month)

> Note: Playwright requires Chromium to be installed on the server. Run `playwright install chromium` after deployment.

### Option B — Serverless (AWS Lambda / Google Cloud Functions)

- Package Playwright as a Lambda Layer (use `playwright-aws-lambda` wrapper)
- Use EventBridge (AWS) or Cloud Scheduler (GCP) as the cron trigger
- Set interval to 15 minutes
- Keep `config.json` in an S3 bucket or Cloud Storage bucket (do not hardcode)

> ⚠️ Do NOT deploy to free-tier platforms with sleep/spin-down behavior (Render free, Railway free). Missed cycles = missed flood alerts.

---

## 9. Prioritized TODO List for Implementer

| # | Task | Priority | Module |
|---|---|---|---|
| 1 | Check DHM site DevTools for a hidden JSON API endpoint. If found, use `requests` instead of Playwright | High | `scraper.py` |
| 2 | Implement Playwright scraper for River Watch table | High | `scraper.py` |
| 3 | Implement multi-recipient WhatsApp dispatch loop | High | `notifier.py` |
| 4 | Build `setup.py` CLI for station selection and recipient management | High | `setup.py` |
| 5 | Implement alert cooldown logic per station | Medium | `analyzer.py` |
| 6 | Add Trend (`Rising`) as a secondary alert trigger (e.g., alert even if below threshold if trend is Rising fast) | Medium | `analyzer.py` |
| 7 | Add Above Danger Level as a second, higher-priority alert tier with a different message template | Medium | `notifier.py` |
| 8 | Validate phone numbers in E.164 format during setup | Medium | `setup.py` |
| 9 | Log all alert history to a `alerts.log` file | Low | `main.py` |
| 10 | Add a daily summary message (e.g., 8 AM each day: all monitored stations and current levels) | Low | `notifier.py` |

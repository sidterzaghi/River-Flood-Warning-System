# River Flood Warning System - Project Status

Last updated: 2026-05-25

## Current State

The first implementation has been scaffolded from `PRD_River_Warning_System_v2.md`.

The repository now contains a Python backend daemon structure for:

- Loading and validating operator configuration from `config.json`
- Scraping DHM Nepal River Watch station data
- Filtering configured stations by `station_no`
- Evaluating water levels against DHM or custom thresholds
- Applying per-station alert cooldowns
- Sending WhatsApp alerts through Twilio or Meta Cloud API
- Managing stations and recipients through an interactive CLI
- Showing a confirmation summary before saving CLI-entered configuration
- Selecting stations in setup by actual DHM station number/index instead of temporary menu numbers
- Sending simulated WhatsApp test alerts to configured recipients
- Continuous daemon mode for 15-minute scraping and 30-minute alert cooldown
- GitHub Actions scheduled workflow for free online checks every 15 minutes
- Persistent `state.json` alert cooldown state for scheduled one-off runs

## Files Added

- `main.py` - orchestration entrypoint for one monitoring cycle
- `main.py --daemon` - continuous monitoring loop using `check_interval_minutes`
- `scraper.py` - DHM River Watch scraping, table parsing, JSON endpoint discovery helper
- `analyzer.py` - station filtering, threshold resolution, alert/cooldown logic
- `notifier.py` - WhatsApp alert formatting and Twilio/Meta dispatch
- `config_manager.py` - config loading, saving, validation, phone number validation
- `setup.py` - interactive CLI for station and recipient management
- `send_test_alert.py` - sends a simulated flood warning for WhatsApp delivery testing
- `.github/workflows/river-watch.yml` - scheduled GitHub Actions workflow
- `config.json` - starter operator configuration
- `.env.example` - template for Twilio/Meta credentials
- `.gitignore` - excludes `.env`, virtualenv, caches, logs
- `requirements.txt` - Python dependencies
- `README.md` - setup and usage instructions
- `tests/` - focused tests for analyzer, config validation, and scraper parsing

## Verified

- Python imports pass for the main modules.
- Scraper helper parsing works against a sample DHM-like HTML table.
- Live DHM River Watch scraping now returns embedded station records from the page's `coordinates` JavaScript array.
- Float parsing handles meter values and missing values such as `--`.
- Analyzer triggers alerts when water level exceeds custom threshold.
- Analyzer suppresses repeated alerts during cooldown.
- Analyzer resets cooldown when water level drops below threshold.
- Setup CLI confirmation summary renders configured stations, recipients, provider, interval, and cooldown before save.
- Test alert script previews a simulated flood warning and asks for confirmation before dispatch.
- WhatsApp API errors now include provider response details such as Twilio code/message.
- `main.py` exits cleanly when no stations are configured.
- Daemon mode is available for repeated scraping using the configured interval.
- Scheduled GitHub Actions workflow is available for laptop-independent free hosting.
- Monitoring cycles now print DHM station/live-level counts and exit nonzero on fatal one-cycle failures.
- `git diff --check` reports no whitespace errors.

## Not Yet Verified

- Whether DHM exposes a hidden JSON/XHR station-data endpoint.
- Real Twilio WhatsApp sending.
- Real Meta Cloud API WhatsApp sending.
- Full `pytest` run in this environment.

## Known Environment Notes

- `pytest` was not installed in the active Python environment, so smoke checks were run with direct Python assertions instead.
- `pytest` has been added to `requirements.txt`.
- Playwright is imported lazily so non-scraper code can be imported before dependencies are installed.
- `python-dotenv` is optional at import time, but should be installed for normal `.env` loading.

## Next Steps

1. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Run the full test suite:

   ```powershell
   python -m pytest -q
   ```

3. Investigate DHM JSON/XHR endpoints:

   ```python
   from scraper import discover_json_candidates
   print(discover_json_candidates())
   ```

4. Configure stations and recipients:

   ```powershell
   python setup.py
   ```

5. Add real WhatsApp credentials to `.env`.

6. Run one monitoring cycle:

   ```powershell
   python main.py
   ```

7. Send a simulated WhatsApp alert:

   ```powershell
   python send_test_alert.py
   ```

## Implementation Caveats

- Alert cooldown state is currently in memory. This matches the PRD's stateless-per-run direction, but means cooldown resets if each cron run starts a fresh process.
- The scraper currently defaults to Playwright and extracts DHM River Watch station data from the embedded `coordinates` JavaScript array. If a stable DHM JSON endpoint is found, `scraper.py` should be updated to prefer that endpoint.
- The PRD file contains encoding artifacts such as `â€”`; the project code avoids copying those artifacts into runtime messages.

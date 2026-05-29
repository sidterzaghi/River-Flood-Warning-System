# River Flood Warning System - Project Status

Last updated: 2026-05-27

## Current State

The repository contains a Python backend daemon structure for:

- Loading and validating operator configuration from `config.json`
- Scraping DHM Nepal River Watch station data
- Filtering configured stations by `station_no`
- Evaluating water levels against DHM or custom thresholds
- Applying per-station alert cooldowns
- Sending Telegram alerts through the Telegram Bot API
- Asking for a Telegram chat ID at runtime when none is configured
- Managing stations and Telegram chat IDs through an interactive CLI
- Showing a confirmation summary before saving CLI-entered configuration
- Sending simulated Telegram test alerts to configured chat IDs
- Continuous daemon mode for 15-minute scraping and 30-minute alert cooldown
- GitHub Actions scheduled workflow for free online checks every 15 minutes
- Persistent `state.json` alert cooldown state for scheduled one-off runs

## Main Files

- `main.py` - orchestration entrypoint for one monitoring cycle or continuous daemon mode
- `scraper.py` - DHM River Watch scraping, table parsing, JSON endpoint discovery helper
- `analyzer.py` - station filtering, threshold resolution, alert/cooldown logic
- `notifier.py` - Telegram alert formatting and dispatch
- `config_manager.py` - config loading, saving, validation, and Telegram chat ID validation
- `setup.py` - interactive CLI for station and Telegram chat ID management
- `send_test_alert.py` - sends a simulated flood warning for Telegram delivery testing
- `.github/workflows/river-watch.yml` - scheduled GitHub Actions workflow
- `config.json` - starter operator configuration
- `.env.example` - template for Telegram bot credentials
- `requirements.txt` - Python dependencies
- `README.md` - setup and usage instructions
- `tests/` - focused tests for analyzer, config validation, and scraper parsing

## Verified

- Python imports pass for the main modules.
- Scraper helper parsing works against a sample DHM-like HTML table.
- Live DHM River Watch scraping returns embedded station records from the page's `coordinates` JavaScript array.
- Float parsing handles meter values and missing values such as `--`.
- Analyzer triggers alerts when water level exceeds custom threshold.
- Analyzer suppresses repeated alerts during cooldown.
- Analyzer resets cooldown when water level drops below threshold.
- Setup CLI confirmation summary renders configured stations, Telegram chat IDs, interval, and cooldown before save.
- Test alert script previews a simulated flood warning and asks for confirmation before dispatch.
- Telegram API errors include response details where provided.
- `main.py` exits cleanly when no stations are configured.
- Daemon mode is available for repeated scraping using the configured interval.
- Scheduled GitHub Actions workflow is available for laptop-independent free hosting.
- Monitoring cycles print DHM station/live-level counts and exit nonzero on fatal one-cycle failures.
- Alert cooldown starts only after at least one Telegram message is delivered.
- Runs print configured Telegram chat ID count and per-station level/threshold checks.

## Not Yet Verified

- Whether DHM exposes a hidden JSON/XHR station-data endpoint.
- Real Telegram Bot API sending with a live bot token.
- Full `pytest` run in this environment.

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

3. Configure stations and Telegram chat IDs:

   ```powershell
   python setup.py
   ```

4. Add your Telegram bot token to `.env`:

   ```text
   TELEGRAM_BOT_TOKEN=123456:your-bot-token
   ```

5. Run one monitoring cycle:

   ```powershell
   python main.py
   ```

6. Send a simulated Telegram alert:

   ```powershell
   python send_test_alert.py
   ```

## Implementation Caveats

- The scraper currently defaults to Playwright and extracts DHM River Watch station data from the embedded `coordinates` JavaScript array. If a stable DHM JSON endpoint is found, `scraper.py` should be updated to prefer that endpoint.
- The PRD file contains old product notes and encoding artifacts; runtime code and operational docs now describe Telegram-only delivery.

# River Flood Warning System

Python daemon for monitoring DHM Nepal River Watch stations and sending WhatsApp flood warnings when configured thresholds are breached.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Fill `.env` with either Twilio or Meta WhatsApp credentials.

## Configure Stations and Recipients

```bash
python setup.py
```

The setup CLI fetches DHM stations, lets you select monitored stations, and validates recipient numbers in E.164 format.
Before saving, it shows a bordered confirmation summary of all configured stations, recipients, provider, interval, and cooldown.

You can also edit `config.json` directly.

## Run One Monitoring Cycle

```bash
python main.py
```

## Run Continuous Monitoring

To scrape DHM every 15 minutes and re-alert every 30 minutes while a station remains above its warning threshold:

```bash
python main.py --daemon
```

These timings come from `config.json`:

```json
"check_interval_minutes": 15,
"alert_cooldown_minutes": 30
```

## Free Online Hosting

The included GitHub Actions workflow runs one monitoring cycle every 15 minutes without keeping your laptop on:

```text
.github/workflows/river-watch.yml
```

Add these GitHub repository secrets before enabling it:

- `CONFIG_JSON` - the full contents of your local `config.json`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `META_ACCESS_TOKEN` and `META_PHONE_NUMBER_ID` if using Meta instead of Twilio

The workflow caches `state.json` so alert cooldowns can survive between scheduled runs.

## Send A Test WhatsApp Alert

After configuring recipients and `.env` credentials, send a simulated flood warning:

```bash
python send_test_alert.py
```

The script previews the test message and asks for confirmation before sending it to all configured recipients.

## Inspect DHM API Candidates

The scraper currently uses Playwright because the public DHM River Watch page is JavaScript-rendered. It also falls back to DHM's Real Time Stream Flow table if River Watch renders without parseable station rows.

To investigate direct JSON endpoints:

```python
from scraper import discover_json_candidates
print(discover_json_candidates())
```

If DHM exposes a stable JSON endpoint, wire it through `fetch_json_endpoint()` in `scraper.py` for a faster production path.

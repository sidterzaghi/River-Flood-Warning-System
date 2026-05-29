# River Flood Warning System

Python daemon for monitoring DHM Nepal River Watch stations and sending Telegram flood warnings when configured thresholds are breached.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Fill `.env` with your Telegram bot token:

```text
TELEGRAM_BOT_TOKEN=123456:your-bot-token
```

Create a bot with BotFather, send a message to the bot from the Telegram account or group that should receive alerts, then use that chat ID when the program asks for it.

## Configure Stations and Telegram Chat IDs

```bash
python setup.py
```

The setup CLI fetches DHM stations, lets you select monitored stations, and validates Telegram chat IDs. Before saving, it shows a bordered confirmation summary of all configured stations, Telegram chat IDs, interval, and cooldown.

You can also edit `config.json` directly:

```json
{
  "monitored_stations": [],
  "telegram_chat_ids": ["123456789"],
  "check_interval_minutes": 15,
  "alert_cooldown_minutes": 30
}
```

If `telegram_chat_ids` is empty, `python main.py` and `python send_test_alert.py` will ask for a Telegram chat ID while running and save it to `config.json`.

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
- `TELEGRAM_BOT_TOKEN`

The workflow caches `state.json` so alert cooldowns can survive between scheduled runs.

## Send A Test Telegram Alert

After configuring `.env`, send a simulated flood warning:

```bash
python send_test_alert.py
```

The script previews the test message and asks for confirmation before sending it to all configured Telegram chat IDs.

## Inspect DHM API Candidates

The scraper currently uses Playwright because the public DHM River Watch page is JavaScript-rendered. It also falls back to DHM's Real Time Stream Flow table if River Watch renders without parseable station rows.

To investigate direct JSON endpoints:

```python
from scraper import discover_json_candidates
print(discover_json_candidates())
```

If DHM exposes a stable JSON endpoint, wire it through `fetch_json_endpoint()` in `scraper.py` for a faster production path.

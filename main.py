import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from analyzer import evaluate_station, filter_monitored_stations
from config_manager import load_config
from notifier import dispatch_alerts
from scraper import scrape_river_watch


STATE_PATH = Path("state.json")
last_alert_times: dict[str, datetime] = {}


def run_cycle() -> bool:
    global last_alert_times
    last_alert_times = load_alert_state()
    config = load_config("config.json")
    station_count = len(config["monitored_stations"])
    print(f"[{now()}] Starting river watch cycle for {station_count} stations...")

    if station_count == 0:
        print("[CONFIG] No monitored stations configured. Run python setup.py to add stations.")
        return True

    try:
        all_stations = scrape_river_watch()
        live_level_count = sum(1 for station in all_stations if station.get("water_level_m") is not None)
        print(f"[DHM] Fetched {len(all_stations)} stations; {live_level_count} have live water levels.")
        monitored = filter_monitored_stations(all_stations, config)

        for station in monitored:
            evaluation = evaluate_station(
                station,
                last_alert_times,
                alert_cooldown_minutes=config["alert_cooldown_minutes"],
            )

            if evaluation["should_alert"]:
                dispatch_alerts(
                    station,
                    evaluation,
                    config["whatsapp_recipients"],
                    provider=config["whatsapp_api_provider"],
                )
                last_alert_times[str(station["station_no"])] = datetime.now()
                print(f"[ALERT SENT] {station['station_name']} - {evaluation['reason']}")
            else:
                print(f"[OK] {station['station_name']} - {evaluation['reason']}")
        save_alert_state(last_alert_times)
        return True
    except Exception as exc:
        print(f"[FATAL ERROR] Cycle failed: {exc}")
        save_alert_state(last_alert_times)
        return False


def run_daemon() -> None:
    while True:
        config = load_config("config.json")
        run_cycle()
        interval_seconds = config["check_interval_minutes"] * 60
        print(f"[{now()}] Next river watch cycle in {config['check_interval_minutes']} minutes.")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="DHM river water-level WhatsApp warning system")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="keep running and scrape on the configured interval",
    )
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    else:
        if not run_cycle():
            sys.exit(1)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_alert_state(path: Path = STATE_PATH) -> dict[str, datetime]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    loaded: dict[str, datetime] = {}
    for station_no, timestamp in data.get("last_alert_times", {}).items():
        try:
            loaded[str(station_no)] = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            continue
    return loaded


def save_alert_state(alert_times: dict[str, datetime], path: Path = STATE_PATH) -> None:
    data = {
        "last_alert_times": {
            station_no: timestamp.isoformat()
            for station_no, timestamp in alert_times.items()
        }
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    main()

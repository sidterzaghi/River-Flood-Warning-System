import json
from typing import Any

from config_manager import is_valid_telegram_chat_id, load_config, save_config
from scraper import scrape_river_watch


CONFIG_PATH = "config.json"


def main() -> None:
    config = load_config(CONFIG_PATH)

    while True:
        print("\n=== River Warning System Setup ===")
        print("[1] Add a river station to monitor")
        print("[2] Remove a station")
        print("[3] Set custom warning level for a station")
        print("[4] Add a Telegram chat ID")
        print("[5] Remove a Telegram chat ID")
        print("[6] View current configuration")
        print("[7] Save and exit")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_station(config)
        elif choice == "2":
            remove_station(config)
        elif choice == "3":
            set_custom_warning_level(config)
        elif choice == "4":
            add_recipient(config)
        elif choice == "5":
            remove_recipient(config)
        elif choice == "6":
            print_confirmation_box(config)
        elif choice == "7":
            print_confirmation_box(config)
            confirm = input("Save this configuration? [Y/n]: ").strip().lower()
            if confirm in {"", "y", "yes"}:
                save_config(config, CONFIG_PATH)
                print("Configuration saved.")
                return
            print("Save cancelled. Returning to setup menu.")
        else:
            print("Invalid option.")


def add_station(config: dict[str, Any]) -> None:
    print("Fetching station list from DHM...")
    stations = scrape_river_watch()
    if not stations:
        print("No stations found.")
        return

    query = input("Filter by basin, district, or station name: ").strip().lower()
    matches = [
        station
        for station in stations
        if not query
        or query in str(station.get("station_name", "")).lower()
        or query in str(station.get("district_name", "")).lower()
        or query in str(station.get("basin_name", "")).lower()
    ]

    displayed_matches = matches[:50]
    for station in displayed_matches:
        print(
            f"- {station.get('station_name')} "
            f"({station.get('station_no')}) - {station.get('district_name')}, {station.get('basin_name')}"
        )

    if len(matches) > 50:
        print(f"Showing first 50 of {len(matches)} matches. Use a narrower filter if needed.")

    station_by_no = {
        str(station.get("station_no", "")).strip(): station
        for station in displayed_matches
        if station.get("station_no") not in (None, "")
    }
    selected_station_no = input("Enter DHM station number/index to add: ").strip()
    station = station_by_no.get(selected_station_no)
    if not station:
        print("Station number not found in the displayed results.")
        return

    dhm_warning = station.get("warning_level_m")
    use_dhm = input(f"Use DHM's published warning level ({dhm_warning} m)? [Y/n]: ").strip().lower()
    use_dhm_warning_level = use_dhm in {"", "y", "yes"}
    custom_level = None

    if not use_dhm_warning_level:
        custom_level = prompt_float("Custom warning level in meters: ")

    station_config = {
        "station_name": station["station_name"],
        "station_no": str(station["station_no"]),
        "custom_warning_level_m": custom_level,
        "use_dhm_warning_level": use_dhm_warning_level,
    }

    config["monitored_stations"] = [
        item
        for item in config["monitored_stations"]
        if str(item["station_no"]) != station_config["station_no"]
    ]
    config["monitored_stations"].append(station_config)
    print(f"Added {station_config['station_name']}.")


def remove_station(config: dict[str, Any]) -> None:
    station = choose_configured_station(config)
    if not station:
        return
    config["monitored_stations"].remove(station)
    print(f"Removed {station['station_name']}.")


def set_custom_warning_level(config: dict[str, Any]) -> None:
    station = choose_configured_station(config)
    if not station:
        return

    use_dhm = input("Use DHM warning level instead of custom? [y/N]: ").strip().lower()
    if use_dhm in {"y", "yes"}:
        station["use_dhm_warning_level"] = True
        station["custom_warning_level_m"] = None
    else:
        station["use_dhm_warning_level"] = False
        station["custom_warning_level_m"] = prompt_float("Custom warning level in meters: ")
    print("Station threshold updated.")


def add_recipient(config: dict[str, Any]) -> None:
    chat_id = input("Telegram chat ID, e.g. 123456789 or -1001234567890: ").strip()
    if not is_valid_telegram_chat_id(chat_id):
        print("Invalid Telegram chat ID.")
        return
    if chat_id not in config["telegram_chat_ids"]:
        config["telegram_chat_ids"].append(chat_id)
    print(f"Current Telegram chat IDs: {config['telegram_chat_ids']}")


def remove_recipient(config: dict[str, Any]) -> None:
    if not config["telegram_chat_ids"]:
        print("No Telegram chat IDs configured.")
        return
    for index, chat_id in enumerate(config["telegram_chat_ids"], start=1):
        print(f"[{index}] {chat_id}")
    selected = input("Select Telegram chat ID to remove: ").strip()
    if not selected.isdigit() or int(selected) < 1 or int(selected) > len(config["telegram_chat_ids"]):
        print("Invalid selection.")
        return
    removed = config["telegram_chat_ids"].pop(int(selected) - 1)
    print(f"Removed {removed}.")


def choose_configured_station(config: dict[str, Any]) -> dict[str, Any] | None:
    stations = config["monitored_stations"]
    if not stations:
        print("No monitored stations configured.")
        return None

    for index, station in enumerate(stations, start=1):
        print(f"[{index}] {station['station_name']} ({station['station_no']})")

    selected = input("Select station: ").strip()
    if not selected.isdigit() or int(selected) < 1 or int(selected) > len(stations):
        print("Invalid station selection.")
        return None
    return stations[int(selected) - 1]


def prompt_float(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print("Enter a valid number.")


def print_confirmation_box(config: dict[str, Any]) -> None:
    lines = build_confirmation_lines(config)
    width = max(len(line) for line in lines) + 4
    border = "+" + "-" * (width - 2) + "+"

    print()
    print(border)
    for line in lines:
        print(f"| {line.ljust(width - 4)} |")
    print(border)
    print()


def build_confirmation_lines(config: dict[str, Any]) -> list[str]:
    lines = ["Configuration Summary", ""]

    stations = config.get("monitored_stations", [])
    lines.append(f"Monitored stations: {len(stations)}")
    if stations:
        for index, station in enumerate(stations, start=1):
            threshold = (
                "DHM warning level"
                if station.get("use_dhm_warning_level")
                else f"Custom {station.get('custom_warning_level_m')} m"
            )
            lines.append(
                f"{index}. {station.get('station_name')} "
                f"({station.get('station_no')}) - {threshold}"
            )
    else:
        lines.append("- None")

    chat_ids = config.get("telegram_chat_ids", [])
    lines.extend(["", f"Telegram chat IDs: {len(chat_ids)}"])
    if chat_ids:
        for index, chat_id in enumerate(chat_ids, start=1):
            lines.append(f"{index}. {chat_id}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            f"Check interval: {config.get('check_interval_minutes')} minutes",
            f"Alert cooldown: {config.get('alert_cooldown_minutes')} minutes",
        ]
    )
    return lines


if __name__ == "__main__":
    main()

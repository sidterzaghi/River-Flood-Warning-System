from typing import Any

from config_manager import is_valid_telegram_chat_id, load_config, save_config
from notifier import build_alert_message, dispatch_alerts


TEST_STATION: dict[str, Any] = {
    "station_no": "TEST-001",
    "station_name": "TEST River at Demo Station",
    "basin_name": "Demo Basin",
    "district_name": "Demo District",
    "water_level_m": 7.25,
    "warning_level_m": 5.0,
    "danger_level_m": 6.5,
    "trend": "Rising",
    "status": "Above Danger Level",
}

TEST_EVALUATION: dict[str, Any] = {
    "should_alert": True,
    "effective_threshold_m": 5.0,
    "threshold_source": "test warning",
    "reason": "This is a simulated flood warning for Telegram delivery testing.",
}


def main() -> None:
    config = load_config("config.json")
    chat_ids = config.get("telegram_chat_ids", [])

    if not chat_ids:
        chat_id = input("Enter Telegram chat ID to receive this test alert: ").strip()
        if not is_valid_telegram_chat_id(chat_id):
            print("Invalid Telegram chat ID.")
            return
        chat_ids = [chat_id]
        config["telegram_chat_ids"] = chat_ids
        save_config(config, "config.json")
        print("Telegram chat ID saved to config.json.")

    print("This will send a TEST flood warning to the configured Telegram chat IDs.")
    print(f"Telegram chat IDs: {', '.join(chat_ids)}")
    print()
    print("Message preview:")
    print("-" * 60)
    print(build_alert_message(TEST_STATION, TEST_EVALUATION))
    print("-" * 60)
    print()

    confirm = input("Send this test Telegram alert now? [y/N]: ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("Test alert cancelled.")
        return

    dispatch_alerts(TEST_STATION, TEST_EVALUATION, chat_ids)


if __name__ == "__main__":
    main()

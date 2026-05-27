from typing import Any

from config_manager import load_config
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
    "reason": "This is a simulated flood warning for WhatsApp delivery testing.",
}


def main() -> None:
    config = load_config("config.json")
    recipients = config.get("whatsapp_recipients", [])
    provider = config.get("whatsapp_api_provider", "twilio")

    if not recipients:
        print("No WhatsApp recipients configured. Run python setup.py first.")
        return

    print("This will send a TEST flood warning to the configured WhatsApp recipients.")
    print(f"Provider: {provider}")
    print(f"Recipients: {', '.join(recipients)}")
    print()
    print("Message preview:")
    print("-" * 60)
    print(build_alert_message(TEST_STATION, TEST_EVALUATION))
    print("-" * 60)
    print()

    confirm = input("Send this test WhatsApp alert now? [y/N]: ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("Test alert cancelled.")
        return

    dispatch_alerts(TEST_STATION, TEST_EVALUATION, recipients, provider=provider)


if __name__ == "__main__":
    main()

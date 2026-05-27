import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "monitored_stations": [],
    "whatsapp_recipients": [],
    "check_interval_minutes": 15,
    "whatsapp_api_provider": "twilio",
    "alert_cooldown_minutes": 30,
}

PHONE_RE = re.compile(r"^\+\d{10,15}$")
SUPPORTED_PROVIDERS = {"twilio", "meta"}


class ConfigError(ValueError):
    """Raised when config.json is missing required structure or values."""


def load_config(path: str | Path = "config.json") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        save_config(DEFAULT_CONFIG.copy(), config_path)
        return DEFAULT_CONFIG.copy()

    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    validate_config(merged)
    return merged


def save_config(config: dict[str, Any], path: str | Path = "config.json") -> None:
    validate_config(config)
    config_path = Path(path)
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)
        file.write("\n")


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config.get("monitored_stations"), list):
        raise ConfigError("monitored_stations must be a list")
    if not isinstance(config.get("whatsapp_recipients"), list):
        raise ConfigError("whatsapp_recipients must be a list")

    for station in config["monitored_stations"]:
        validate_station_config(station)

    for number in config["whatsapp_recipients"]:
        if not is_valid_phone_number(number):
            raise ConfigError(f"Invalid WhatsApp recipient number: {number}")

    interval = config.get("check_interval_minutes")
    if not isinstance(interval, int) or interval < 1:
        raise ConfigError("check_interval_minutes must be a positive integer")

    cooldown = config.get("alert_cooldown_minutes")
    if not isinstance(cooldown, int) or cooldown < 0:
        raise ConfigError("alert_cooldown_minutes must be a non-negative integer")

    provider = config.get("whatsapp_api_provider")
    if provider not in SUPPORTED_PROVIDERS:
        raise ConfigError(
            f"whatsapp_api_provider must be one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )


def validate_station_config(station: dict[str, Any]) -> None:
    required = {"station_no", "station_name", "custom_warning_level_m", "use_dhm_warning_level"}
    missing = required - set(station)
    if missing:
        raise ConfigError(f"Station config missing required fields: {', '.join(sorted(missing))}")

    if not str(station["station_no"]).strip():
        raise ConfigError("station_no cannot be empty")
    if not str(station["station_name"]).strip():
        raise ConfigError("station_name cannot be empty")
    if not isinstance(station["use_dhm_warning_level"], bool):
        raise ConfigError("use_dhm_warning_level must be true or false")

    custom_level = station["custom_warning_level_m"]
    if not station["use_dhm_warning_level"] and custom_level is None:
        raise ConfigError("custom_warning_level_m is required when use_dhm_warning_level is false")
    if custom_level is not None and not isinstance(custom_level, (int, float)):
        raise ConfigError("custom_warning_level_m must be a number or null")


def is_valid_phone_number(value: str) -> bool:
    return bool(PHONE_RE.fullmatch(value or ""))

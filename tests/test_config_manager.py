import pytest

from config_manager import ConfigError, is_valid_telegram_chat_id, validate_config


def test_telegram_chat_id_validation_accepts_numeric_ids():
    assert is_valid_telegram_chat_id("123456789")
    assert is_valid_telegram_chat_id("-1001234567890")


def test_telegram_chat_id_validation_accepts_channel_usernames():
    assert is_valid_telegram_chat_id("@river_alerts")


def test_telegram_chat_id_validation_rejects_empty_values():
    assert not is_valid_telegram_chat_id("")


def test_validate_config_rejects_missing_custom_threshold_when_required():
    config = {
        "monitored_stations": [
            {
                "station_name": "Bagmati River at Gaurighat",
                "station_no": "501",
                "custom_warning_level_m": None,
                "use_dhm_warning_level": False,
            }
        ],
        "telegram_chat_ids": [],
        "check_interval_minutes": 15,
        "alert_cooldown_minutes": 60,
    }

    with pytest.raises(ConfigError):
        validate_config(config)

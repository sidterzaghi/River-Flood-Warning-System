import pytest

from config_manager import ConfigError, is_valid_phone_number, validate_config


def test_phone_validation_accepts_e164_numbers():
    assert is_valid_phone_number("+9779800000001")


def test_phone_validation_rejects_local_numbers():
    assert not is_valid_phone_number("9800000001")


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
        "whatsapp_recipients": [],
        "check_interval_minutes": 15,
        "whatsapp_api_provider": "twilio",
        "alert_cooldown_minutes": 60,
    }

    with pytest.raises(ConfigError):
        validate_config(config)

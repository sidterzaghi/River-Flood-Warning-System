from datetime import datetime, timedelta

from analyzer import evaluate_station, filter_monitored_stations


def test_filter_monitored_stations_merges_config_by_station_no():
    all_stations = [
        {"station_no": "501", "station_name": "Live", "water_level_m": 4.0},
        {"station_no": "999", "station_name": "Other", "water_level_m": 1.0},
    ]
    config = {
        "monitored_stations": [
            {
                "station_no": "501",
                "station_name": "Configured",
                "custom_warning_level_m": 3.5,
                "use_dhm_warning_level": False,
            }
        ]
    }

    result = filter_monitored_stations(all_stations, config)

    assert len(result) == 1
    assert result[0]["station_no"] == "501"
    assert result[0]["custom_warning_level_m"] == 3.5


def test_evaluate_station_alerts_when_water_exceeds_custom_threshold():
    station = {
        "station_no": "501",
        "water_level_m": 5.2,
        "custom_warning_level_m": 4.5,
        "use_dhm_warning_level": False,
        "trend": "Rising",
    }

    result = evaluate_station(station, {}, now=datetime(2026, 5, 25, 14, 30))

    assert result["should_alert"] is True
    assert result["effective_threshold_m"] == 4.5
    assert "exceeds custom threshold" in result["reason"]


def test_evaluate_station_suppresses_during_cooldown():
    now = datetime(2026, 5, 25, 14, 30)
    station = {
        "station_no": "501",
        "water_level_m": 5.2,
        "custom_warning_level_m": 4.5,
        "use_dhm_warning_level": False,
    }
    last_alert_times = {"501": now - timedelta(minutes=10)}

    result = evaluate_station(station, last_alert_times, alert_cooldown_minutes=60, now=now)

    assert result["should_alert"] is False
    assert "cooldown" in result["reason"]


def test_evaluate_station_resets_cooldown_below_threshold():
    station = {
        "station_no": "501",
        "water_level_m": 3.0,
        "custom_warning_level_m": 4.5,
        "use_dhm_warning_level": False,
    }
    last_alert_times = {"501": datetime(2026, 5, 25, 14, 0)}

    result = evaluate_station(station, last_alert_times)

    assert result["should_alert"] is False
    assert "501" not in last_alert_times

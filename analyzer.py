from datetime import datetime, timedelta
from typing import Any


def filter_monitored_stations(
    all_stations: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    stations_by_no = {str(station.get("station_no")): station for station in all_stations}
    monitored: list[dict[str, Any]] = []

    for station_config in config.get("monitored_stations", []):
        station_no = str(station_config["station_no"])
        live_station = stations_by_no.get(station_no)
        if not live_station:
            print(f"[WARN] Configured station not found in DHM data: {station_no}")
            continue

        merged = live_station.copy()
        merged.update(station_config)
        monitored.append(merged)

    return monitored


def evaluate_station(
    station: dict[str, Any],
    last_alert_times: dict[str, datetime],
    alert_cooldown_minutes: int = 60,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    station_no = str(station.get("station_no", ""))
    water_level = station.get("water_level_m")
    threshold, threshold_source = resolve_threshold(station)

    if water_level is None:
        return {
            "should_alert": False,
            "effective_threshold_m": threshold,
            "threshold_source": threshold_source,
            "reason": "Current water level is unavailable",
        }

    if threshold is None:
        return {
            "should_alert": False,
            "effective_threshold_m": None,
            "threshold_source": threshold_source,
            "reason": "No warning threshold is available",
        }

    if water_level < threshold:
        last_alert_times.pop(station_no, None)
        return {
            "should_alert": False,
            "effective_threshold_m": threshold,
            "threshold_source": threshold_source,
            "reason": f"Water level {water_level:.2f}m is below {threshold_source} threshold {threshold:.2f}m",
        }

    last_sent = last_alert_times.get(station_no)
    if last_sent and now - last_sent < timedelta(minutes=alert_cooldown_minutes):
        remaining = timedelta(minutes=alert_cooldown_minutes) - (now - last_sent)
        return {
            "should_alert": False,
            "effective_threshold_m": threshold,
            "threshold_source": threshold_source,
            "reason": f"Threshold exceeded, but alert cooldown remains for {remaining}",
        }

    trend = station.get("trend") or "Unknown"
    return {
        "should_alert": True,
        "effective_threshold_m": threshold,
        "threshold_source": threshold_source,
        "reason": (
            f"Water level {water_level:.2f}m exceeds {threshold_source} "
            f"threshold {threshold:.2f}m (Trend: {trend})"
        ),
    }


def resolve_threshold(station: dict[str, Any]) -> tuple[float | None, str]:
    if station.get("use_dhm_warning_level"):
        return station.get("warning_level_m"), "DHM warning"
    return station.get("custom_warning_level_m"), "custom"

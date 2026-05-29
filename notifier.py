import os
from datetime import datetime
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


TELEGRAM_API_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"


def dispatch_alerts(
    station: dict[str, Any],
    evaluation: dict[str, Any],
    chat_ids: list[str],
) -> int:
    load_dotenv()
    message = build_alert_message(station, evaluation)
    sent_count = 0

    if not chat_ids:
        print("[TELEGRAM] No chat IDs configured; alert was not sent.")
        return sent_count

    for chat_id in chat_ids:
        try:
            send_telegram_message(chat_id, message)
            print(f"[TELEGRAM] Alert sent to {chat_id}")
            sent_count += 1
        except Exception as exc:
            print(f"[TELEGRAM] Failed to send alert to {chat_id}: {exc}")
    return sent_count


def build_alert_message(station: dict[str, Any], evaluation: dict[str, Any]) -> str:
    water_level = _format_meters(station.get("water_level_m"))
    threshold = _format_meters(evaluation.get("effective_threshold_m"))
    threshold_source = evaluation.get("threshold_source", "warning")
    station_name = station.get("station_name", "Unknown station")
    district = station.get("district_name") or "Unknown"
    basin = station.get("basin_name") or "Unknown"
    trend = station.get("trend") or "Unknown"
    now = datetime.now().strftime("%Y-%m-%d %H:%M NPT")

    return "\n".join(
        [
            f"FLOOD WARNING - {station_name}",
            f"District: {district} | Basin: {basin}",
            f"Current Level: {water_level}",
            f"Threshold: {threshold} ({threshold_source})",
            f"Trend: {trend}",
            f"Time: {now}",
            "Source: DHM Nepal (dhm.gov.np)",
        ]
    )


def send_telegram_message(chat_id: str, message: str) -> None:
    token = _required_env("TELEGRAM_BOT_TOKEN")
    url = TELEGRAM_API_TEMPLATE.format(token=token)

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    raise_for_status_with_details(response, "Telegram")


def raise_for_status_with_details(response: requests.Response, provider: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = _extract_error_detail(response)
        raise RuntimeError(f"{provider} API error {response.status_code}: {detail}") from exc


def _extract_error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or response.reason

    if isinstance(data, dict):
        parts = []
        for key in ("error_code", "description", "code", "message", "more_info", "status"):
            if data.get(key):
                parts.append(f"{key}={data[key]}")
        if parts:
            return "; ".join(parts)
    return str(data)[:500]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _format_meters(value: Any) -> str:
    if value is None:
        return "Unavailable"
    return f"{float(value):.2f} m"

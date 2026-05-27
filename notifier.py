import os
from datetime import datetime
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


TWILIO_API_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
META_API_TEMPLATE = "https://graph.facebook.com/v18.0/{phone_number_id}/messages"


def dispatch_alerts(
    station: dict[str, Any],
    evaluation: dict[str, Any],
    recipients: list[str],
    provider: str = "twilio",
) -> int:
    load_dotenv()
    message = build_alert_message(station, evaluation)
    sent_count = 0

    if not recipients:
        print("[WHATSAPP] No recipients configured; alert was not sent.")
        return sent_count

    for recipient in recipients:
        try:
            if provider == "twilio":
                send_twilio_message(recipient, message)
            elif provider == "meta":
                send_meta_message(recipient, message)
            else:
                raise ValueError(f"Unsupported WhatsApp provider: {provider}")
            print(f"[WHATSAPP] Alert sent to {recipient}")
            sent_count += 1
        except Exception as exc:
            print(f"[WHATSAPP] Failed to send alert to {recipient}: {exc}")
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


def send_twilio_message(recipient: str, message: str) -> None:
    sid = _required_env("TWILIO_ACCOUNT_SID")
    token = _required_env("TWILIO_AUTH_TOKEN")
    sender = _required_env("TWILIO_WHATSAPP_FROM")
    url = TWILIO_API_TEMPLATE.format(sid=sid)

    response = requests.post(
        url,
        auth=(sid, token),
        data={
            "From": sender,
            "To": f"whatsapp:{recipient}",
            "Body": message,
        },
        timeout=30,
    )
    raise_for_status_with_details(response, "Twilio")


def send_meta_message(recipient: str, message: str) -> None:
    token = _required_env("META_ACCESS_TOKEN")
    phone_number_id = _required_env("META_PHONE_NUMBER_ID")
    url = META_API_TEMPLATE.format(phone_number_id=phone_number_id)

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": recipient.lstrip("+"),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        },
        timeout=30,
    )
    raise_for_status_with_details(response, "Meta")


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
        for key in ("code", "message", "more_info", "status"):
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

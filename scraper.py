import json
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup


DHM_RIVER_WATCH_URL = "https://dhm.gov.np/hydrology/river-watch"
DHM_REALTIME_STREAM_URL = "https://dhm.gov.np/bhasa/hydrology_realtime-stream/en"
SCRAPE_URLS = [DHM_RIVER_WATCH_URL, DHM_REALTIME_STREAM_URL]
DEFAULT_TIMEOUT_MS = 30_000
RETRY_DELAY_SECONDS = 10
MAX_RETRIES = 3

EXPECTED_FIELDS = [
    "station_no",
    "basin_name",
    "station_name",
    "district_name",
    "water_level_m",
    "warning_level_m",
    "danger_level_m",
    "trend",
    "status",
]


def scrape_river_watch() -> list[dict[str, Any]]:
    """
    Return DHM River Watch station records.

    The function first tries known direct JSON endpoints if configured later,
    then falls back to Playwright because the public page is JavaScript-rendered.
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            records = []
            errors = []
            for url in SCRAPE_URLS:
                try:
                    records = _scrape_with_requests(url)
                    if records:
                        break
                    errors.append(f"{url}: no station rows parsed with requests")
                except Exception as exc:
                    errors.append(f"{url}: requests failed: {exc}")

                try:
                    records = _scrape_with_playwright(url)
                    if records:
                        break
                    errors.append(f"{url}: no station rows parsed with Playwright")
                except Exception as exc:
                    errors.append(f"{url}: Playwright failed: {exc}")
            if not records:
                raise RuntimeError("; ".join(errors))
            return records
        except Exception as exc:
            last_error = exc
            print(f"[SCRAPER] Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"DHM River Watch scraping failed after {MAX_RETRIES} attempts") from last_error


def discover_json_candidates(timeout: int = 20) -> list[str]:
    """
    Capture XHR/fetch URLs requested by the River Watch page.

    This helps confirm whether DHM exposes a JSON endpoint that can replace
    browser rendering in production.
    """
    candidates: list[str] = []
    sync_playwright = _load_sync_playwright()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def capture(response: Any) -> None:
            request = response.request
            resource_type = request.resource_type
            content_type = response.headers.get("content-type", "")
            if resource_type in {"xhr", "fetch"} or "json" in content_type.lower():
                candidates.append(response.url)

        page.on("response", capture)
        page.goto(DHM_RIVER_WATCH_URL, wait_until="networkidle", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_timeout(timeout * 1000)
        browser.close()

    return sorted(set(candidates))


def _scrape_with_playwright(url: str = DHM_RIVER_WATCH_URL) -> list[dict[str, Any]]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_selector("table", timeout=DEFAULT_TIMEOUT_MS)
        _trigger_dhm_table_load(page)
        html = page.content()
        browser.close()

    return parse_river_watch_html(html)


def _scrape_with_requests(url: str = DHM_RIVER_WATCH_URL) -> list[dict[str, Any]]:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    return parse_river_watch_html(response.text)


def fetch_json_endpoint(url: str) -> list[dict[str, Any]]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    return normalize_json_payload(data)


def normalize_json_payload(data: Any) -> list[dict[str, Any]]:
    rows = _find_station_like_rows(data)
    return [normalize_station_record(row) for row in rows]


def parse_river_watch_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    embedded = _extract_embedded_json_records(soup)
    if embedded:
        return embedded

    tables = soup.find_all("table")
    if not tables:
        return []

    rows: list[dict[str, Any]] = []

    for table in tables:
        headers = _extract_table_headers(table)
        for tr in table.select("tbody tr"):
            cells = [_clean_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if not cells or all(not cell for cell in cells):
                continue
            parsed = _parse_table_row(headers, cells)
            if _parsed_row_has_station_data(parsed):
                rows.append(parsed)

    return [row for row in rows if row.get("station_no") or row.get("station_name")]


def normalize_station_record(row: dict[str, Any]) -> dict[str, Any]:
    lowered = {str(key).lower().strip(): value for key, value in row.items()}

    def first(*keys: str) -> Any:
        for key in keys:
            if key in lowered and lowered[key] not in (None, ""):
                return lowered[key]
        return None

    return {
        "station_no": str(
            first("station_no", "stationno", "station id", "station_id", "stationindex", "station_index", "id")
            or ""
        ).strip(),
        "basin_name": _as_text(first("basin_name", "basin", "basinname")),
        "station_name": _as_text(first("station_name", "station", "stationname", "name")),
        "district_name": _as_text(first("district_name", "district", "districtname")),
        "water_level_m": _parse_water_level(first("water_level_m", "waterlevel", "water_level", "level", "current level")),
        "warning_level_m": parse_float(first("warning_level_m", "warninglevel", "warning_level", "warning")),
        "danger_level_m": parse_float(first("danger_level_m", "dangerlevel", "danger_level", "danger")),
        "trend": _normalize_trend(first("trend", "tendency", "steady")),
        "status": _as_text(first("status", "condition")),
    }


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text in {"--", "-", "N/A", "NA"}:
        return None

    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(match.group(0)) if match else None


def _parse_table_row(headers: list[str], cells: list[str]) -> dict[str, Any]:
    mapped = _map_cells_by_header(headers, cells) if headers else {}
    if not mapped:
        mapped = _map_cells_by_position(cells)
    return normalize_station_record(mapped)


def _map_cells_by_header(headers: list[str], cells: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for header, value in zip(headers, cells):
        key = _canonical_header(header)
        if key:
            mapped[key] = value
    return mapped


def _map_cells_by_position(cells: list[str]) -> dict[str, str]:
    if len(cells) >= 7:
        # DHM Real Time Stream Flow table:
        # S.No., Basin Name, Station Index, Station Name, District Name, Water Level, Discharge
        realtime_keys = [
            "_serial_no",
            "basin_name",
            "station_no",
            "station_name",
            "district_name",
            "water_level_m",
            "discharge",
        ]
        return dict(zip(realtime_keys, cells))
    keys = EXPECTED_FIELDS[: len(cells)]
    return dict(zip(keys, cells))


def _canonical_header(header: str) -> str | None:
    value = header.lower().replace(".", "").replace("_", " ")
    if value in {"s no", "sno", "sn"}:
        return None
    if "station" in value and "index" in value:
        return "station_no"
    if "station" in value and ("no" in value or "id" in value):
        return "station_no"
    if "basin" in value:
        return "basin_name"
    if "station" in value or "river" in value:
        return "station_name"
    if "district" in value:
        return "district_name"
    if "water" in value or "level" in value and "warning" not in value and "danger" not in value:
        return "water_level_m"
    if "warning" in value:
        return "warning_level_m"
    if "danger" in value:
        return "danger_level_m"
    if "trend" in value or "tendency" in value:
        return "trend"
    if "status" in value or "condition" in value:
        return "status"
    if "discharge" in value:
        return "discharge"
    return None


def _extract_table_headers(table: Any) -> list[str]:
    headers = [_clean_text(cell.get_text(" ", strip=True)) for cell in table.select("thead th")]
    if headers:
        return headers

    first_row = table.find("tr")
    if not first_row:
        return []

    header_cells = first_row.find_all("th")
    if header_cells:
        return [_clean_text(cell.get_text(" ", strip=True)) for cell in header_cells]
    return []


def _parsed_row_has_station_data(row: dict[str, Any]) -> bool:
    return bool(row.get("station_name")) and row.get("water_level_m") is not None


def _trigger_dhm_table_load(page: Any) -> None:
    try:
        page.evaluate(
            """
            () => {
              const submit = document.querySelector('#submit');
              if (submit) submit.click();
            }
            """
        )
        page.wait_for_function(
            "() => document.querySelectorAll('#riverwatchtableview tr').length > 0",
            timeout=15_000,
        )
    except Exception:
        page.wait_for_timeout(1500)


def _extract_embedded_json_records(soup: BeautifulSoup) -> list[dict[str, Any]]:
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        if "station" not in text.lower():
            continue
        coordinates = _extract_coordinates_array(text)
        if coordinates:
            return [normalize_station_record(row) for row in coordinates]
        for candidate in _json_objects_from_text(text):
            rows = _find_station_like_rows(candidate)
            if rows:
                return [normalize_station_record(row) for row in rows]
    return []


def _extract_coordinates_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"var\s+coordinates\s*=\s*(\[.*?\]);", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, dict)]


def _json_objects_from_text(text: str) -> list[Any]:
    objects: list[Any] = []
    for match in re.finditer(r"(\{.*\}|\[.*\])", text, re.DOTALL):
        try:
            objects.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return objects


def _find_station_like_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        dict_rows = [item for item in data if isinstance(item, dict)]
        if dict_rows and any(_looks_like_station(row) for row in dict_rows):
            return dict_rows
        for item in data:
            found = _find_station_like_rows(item)
            if found:
                return found
    elif isinstance(data, dict):
        if _looks_like_station(data):
            return [data]
        for value in data.values():
            found = _find_station_like_rows(value)
            if found:
                return found
    return []


def _looks_like_station(row: dict[str, Any]) -> bool:
    keys = {str(key).lower() for key in row}
    return any("station" in key for key in keys) and any(
        "level" in key or "warning" in key or "danger" in key for key in keys
    )


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _parse_water_level(value: Any) -> float | None:
    if isinstance(value, dict):
        return parse_float(value.get("value"))
    return parse_float(value)


def _normalize_trend(value: Any) -> str:
    text = _as_text(value)
    return text.title() if text.isupper() else text


def _load_sync_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for DHM scraping. Install dependencies with "
            "`pip install -r requirements.txt` and then run `playwright install chromium`."
        ) from exc
    return sync_playwright

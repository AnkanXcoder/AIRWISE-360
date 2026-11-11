"""
Historical OpenAQ ingestion for AIRWISE 360.

Fetches historical observations sensor-by-sensor and stores them using
the existing AIRWISE SQLite schema.
"""

from datetime import datetime, timedelta, timezone
import math

from backend.database import save_measurements
from backend.services.openaq_service import openaq_service


POLLUTANT_ALIASES = {
    "pm2.5": "pm25",
    "pm_25": "pm25",
    "pm25": "pm25",
    "pm10": "pm10",
    "no2": "no2",
    "nitrogen dioxide": "no2",
    "so2": "so2",
    "sulfur dioxide": "so2",
    "sulphur dioxide": "so2",
    "co": "co",
    "carbon monoxide": "co",
    "o3": "o3",
    "ozone": "o3",
    "nh3": "nh3",
    "ammonia": "nh3",
    "pb": "pb",
    "lead": "pb",
}

SUPPORTED_POLLUTANTS = set(POLLUTANT_ALIASES.values())


def normalize_pollutant_name(name):
    if not name:
        return None
    return POLLUTANT_ALIASES.get(str(name).strip().lower())


def _parse_observation_timestamp(item):
    datetime_info = item.get("datetime") or {}
    raw_timestamp = datetime_info.get("utc") or datetime_info.get("local")

    if not raw_timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(raw_timestamp).replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None

    # Do not silently interpret timezone-naive timestamps as UTC.
    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def ingest_station_historical_data(
    location_id,
    station_name,
    hours=36,
    limit=1000,
    max_pages=5,
):
    """
    Fetch historical observations for every supported sensor at a location.

    The default 36-hour fetch window provides a small buffer around the
    24-hour CPCB calculation window. The CPCB service applies its own
    calculation window and data-completeness checks.
    """

    if isinstance(location_id, bool) or not str(location_id).isdigit():
        raise ValueError("location_id must be a positive integer")

    location_id = int(location_id)
    if location_id <= 0:
        raise ValueError("location_id must be a positive integer")

    if not isinstance(hours, int) or not 24 <= hours <= 168:
        raise ValueError("hours must be an integer between 24 and 168")

    retrieved_at = datetime.now(timezone.utc).isoformat()
    datetime_to = datetime.now(timezone.utc)
    datetime_from = datetime_to - timedelta(hours=hours)

    sensors = openaq_service.get_sensors(location_id)
    if not sensors:
        return {
            "status": "NO_SENSORS",
            "location_id": location_id,
            "station_name": station_name,
            "sensors_found": 0,
            "supported_sensors": 0,
            "records_fetched": 0,
            "records_saved": 0,
            "sensor_errors": [],
            "message": "OpenAQ returned no sensors for this station.",
        }

    all_records = []
    sensor_errors = []
    supported_sensor_count = 0

    for sensor in sensors:
        if not isinstance(sensor, dict):
            continue

        sensor_id = sensor.get("id")
        parameter = sensor.get("parameter") or {}
        pollutant_name = parameter.get("name")
        pollutant = normalize_pollutant_name(pollutant_name)
        unit = parameter.get("units")

        if pollutant not in SUPPORTED_POLLUTANTS:
            continue

        if not isinstance(sensor_id, int) or sensor_id <= 0:
            continue

        supported_sensor_count += 1

        try:
            observations = openaq_service.get_historical_measurements(
                sensor_id=sensor_id,
                datetime_from=datetime_from.isoformat(),
                datetime_to=datetime_to.isoformat(),
                limit=limit,
                max_pages=max_pages,
            )
        except Exception as error:
            sensor_errors.append({
                "sensor_id": sensor_id,
                "pollutant": pollutant,
                "error": str(error),
            })
            continue

        for item in observations:
            if not isinstance(item, dict):
                continue

            timestamp = _parse_observation_timestamp(item)
            if timestamp is None:
                continue

            value = item.get("value")
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            if not math.isfinite(value) or value < 0:
                continue

            # Keep observations only within the requested fetch window.
            if timestamp < datetime_from or timestamp > datetime_to:
                continue

            all_records.append({
                "sensor_id": sensor_id,
                "pollutant": pollutant,
                "value": value,
                "unit": unit,
                "timestamp": timestamp.isoformat(),
                "freshness": "HISTORICAL",
            })

    saved_count = save_measurements(
        records=all_records,
        location_id=location_id,
        station_name=station_name,
        retrieved_at=retrieved_at,
        source="OpenAQ",
    )

    if all_records and not sensor_errors:
        status = "SUCCESS"
    elif all_records and sensor_errors:
        status = "PARTIAL_SUCCESS"
    elif sensor_errors:
        status = "FETCH_ERRORS"
    else:
        status = "NO_HISTORICAL_RECORDS"

    return {
        "status": status,
        "location_id": location_id,
        "station_name": station_name,
        "fetch_window_hours": hours,
        "datetime_from": datetime_from.isoformat(),
        "datetime_to": datetime_to.isoformat(),
        "sensors_found": len(sensors),
        "supported_sensors": supported_sensor_count,
        "records_fetched": len(all_records),
        "records_saved_or_updated": saved_count,
        "sensor_errors": sensor_errors,
        "message": (
            "Historical ingestion completed. Check the CPCB AQI endpoint "
            "again to evaluate data sufficiency."
            if all_records
            else "No valid historical observations were fetched. "
                 "Check sensor availability and the reported errors."
        ),
    }

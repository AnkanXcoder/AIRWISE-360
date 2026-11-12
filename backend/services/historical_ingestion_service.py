
"""
Historical OpenAQ ingestion for AIRWISE 360.

Fetches historical observations sensor-by-sensor and stores them
in the configured AIRWISE database (SQLite or PostgreSQL).
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
    """Normalize OpenAQ pollutant names."""

    if not name:
        return None

    return POLLUTANT_ALIASES.get(str(name).strip().lower())


def _parse_observation_timestamp(item):
    """
    Extract timestamps from OpenAQ V3 historical observations.

    OpenAQ V3 structure:
        period:
            datetimeFrom:
                utc: 2026-11-11T14:30:00Z
                local: ...

    Retains compatibility with older datetime structures.
    """

    if not isinstance(item, dict):
        return None

    period = item.get("period") or {}

    datetime_info = (
        item.get("datetime")
        or period.get("datetimeFrom")
        or {}
    )

    if not isinstance(datetime_info, dict):
        return None

    raw_timestamp = (
        datetime_info.get("utc")
        or datetime_info.get("local")
    )

    if not raw_timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(raw_timestamp).replace("Z", "+00:00")
        )

    except (TypeError, ValueError):
        return None

    # Reject timestamps without timezone information.
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
    Fetch historical observations for supported sensors
    and save them into the configured database.

    The 36-hour default provides a buffer around the
    24-hour CPCB AQI calculation window.
    """

    # --------------------------------------------------
    # 1. VALIDATE INPUT
    # --------------------------------------------------

    if isinstance(location_id, bool):
        raise ValueError("location_id must be a positive integer")

    if not str(location_id).isdigit():
        raise ValueError("location_id must be a positive integer")

    location_id = int(location_id)

    if location_id <= 0:
        raise ValueError("location_id must be a positive integer")

    if (
        isinstance(hours, bool)
        or not isinstance(hours, int)
        or not 24 <= hours <= 168
    ):
        raise ValueError(
            "hours must be an integer between 24 and 168"
        )

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 1000
    ):
        raise ValueError("limit must be between 1 and 1000")

    if (
        isinstance(max_pages, bool)
        or not isinstance(max_pages, int)
        or max_pages < 1
    ):
        raise ValueError("max_pages must be a positive integer")

    # --------------------------------------------------
    # 2. DEFINE HISTORICAL TIME WINDOW
    # --------------------------------------------------

    datetime_to = datetime.now(timezone.utc)
    datetime_from = datetime_to - timedelta(hours=hours)

    retrieved_at = datetime_to.isoformat()

    # --------------------------------------------------
    # 3. FETCH STATION SENSORS
    # --------------------------------------------------

    sensors = openaq_service.get_sensors(location_id)

    if not sensors:
        return {
            "status": "NO_SENSORS",
            "location_id": location_id,
            "station_name": station_name,
            "sensors_found": 0,
            "supported_sensors": 0,
            "records_fetched": 0,
            "records_saved_or_updated": 0,
            "sensor_errors": [],
            "message": "OpenAQ returned no sensors for this station.",
        }

    all_records = []
    sensor_errors = []
    supported_sensor_count = 0

    # Prevent duplicate observations within this ingestion batch.
    seen_records = set()

    # --------------------------------------------------
    # 4. PROCESS EACH SENSOR
    # --------------------------------------------------

    for sensor in sensors:

        if not isinstance(sensor, dict):
            continue

        sensor_id = sensor.get("id")

        parameter = sensor.get("parameter") or {}

        if not isinstance(parameter, dict):
            continue

        pollutant_name = parameter.get("name")
        pollutant = normalize_pollutant_name(pollutant_name)
        unit = parameter.get("units")

        if pollutant not in SUPPORTED_POLLUTANTS:
            continue

        if (
            isinstance(sensor_id, bool)
            or not isinstance(sensor_id, int)
            or sensor_id <= 0
        ):
            continue

        supported_sensor_count += 1

        # --------------------------------------------------
        # 5. FETCH HISTORICAL SENSOR OBSERVATIONS
        # --------------------------------------------------

        try:

            observations = (
                openaq_service.get_historical_measurements(
                    sensor_id=sensor_id,
                    datetime_from=datetime_from.isoformat(),
                    datetime_to=datetime_to.isoformat(),
                    limit=limit,
                    max_pages=max_pages,
                )
            )

        except Exception as error:

            sensor_errors.append({
                "sensor_id": sensor_id,
                "pollutant": pollutant,
                "error": str(error),
            })

            continue

        # --------------------------------------------------
        # 6. VALIDATE AND NORMALIZE OBSERVATIONS
        # --------------------------------------------------

        for item in observations:

            if not isinstance(item, dict):
                continue

            # IMPORTANT:
            # OpenAQ V3 timestamp is in:
            # item["period"]["datetimeFrom"]["utc"]

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

            # Ensure observation belongs to requested window.
            if timestamp < datetime_from:
                continue

            if timestamp > datetime_to:
                continue

            timestamp_string = timestamp.isoformat()

            # Avoid duplicate observations in the same batch.
            record_key = (sensor_id, timestamp_string)

            if record_key in seen_records:
                continue

            seen_records.add(record_key)

            # --------------------------------------------------
            # 7. PREPARE DATABASE RECORD
            # --------------------------------------------------

            all_records.append({
                "sensor_id": sensor_id,
                "pollutant": pollutant,
                "value": value,
                "unit": unit,
                "timestamp": timestamp_string,
                "freshness": "HISTORICAL",
            })

    # --------------------------------------------------
    # 8. SAVE RECORDS TO DATABASE
    # --------------------------------------------------

    saved_count = 0

    if all_records:

        saved_count = save_measurements(
            records=all_records,
            location_id=location_id,
            station_name=station_name,
            retrieved_at=retrieved_at,
            source="OpenAQ",
        )

    # --------------------------------------------------
    # 9. DETERMINE INGESTION STATUS
    # --------------------------------------------------

    if all_records and not sensor_errors:
        status = "SUCCESS"

    elif all_records and sensor_errors:
        status = "PARTIAL_SUCCESS"

    elif sensor_errors:
        status = "FETCH_ERRORS"

    else:
        status = "NO_HISTORICAL_RECORDS"

    # --------------------------------------------------
    # 10. RETURN INGESTION SUMMARY
    # --------------------------------------------------

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
            "Historical ingestion completed. "
            "Check the CPCB AQI endpoint to evaluate "
            "data sufficiency."
            if all_records
            else (
                "No valid historical observations were fetched. "
                "Check sensor availability and sensor errors."
            )
        ),
    }

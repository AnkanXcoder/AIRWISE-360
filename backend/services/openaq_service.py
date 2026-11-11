
import os
from pathlib import Path
from datetime import datetime, timezone

import requests
import math
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv



# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3"

REQUEST_TIMEOUT = 30


# --------------------------------------------------
# API CLIENT
# --------------------------------------------------

class OpenAQService:

    def __init__(self):

        # Keep the API application importable even when the optional
        # OpenAQ credential has not yet been configured. Requests fail
        # with a clear runtime error only when an OpenAQ endpoint is used.
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "AIRWISE-360/1.0"
        }
        if API_KEY:
            self.headers["X-API-Key"] = API_KEY

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Retry temporary network and server failures.
        retry_strategy = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
            raise_on_status=False
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # --------------------------------------------------
    # COMMON API REQUEST
    # --------------------------------------------------

    def _get(self, endpoint):

        if not API_KEY:
            raise RuntimeError(
                "OPENAQ_API_KEY is not configured. Add it to the backend .env "
                "file or hosting environment variables."
            )

        url = f"{BASE_URL}{endpoint}"

        try:

            response = self.session.get(
                url,
                params={
                    "limit": 100,
                    "page": 1
                },
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            try:
                data = response.json()

            except requests.exceptions.JSONDecodeError as error:
                raise RuntimeError(
                    "OpenAQ returned an invalid JSON response"
                ) from error

            results = data.get("results", [])

            if not isinstance(results, list):
                raise RuntimeError(
                    "Unexpected OpenAQ response format"
                )

            return results

        except requests.exceptions.HTTPError as error:

            status_code = error.response.status_code

            raise RuntimeError(
                f"OpenAQ HTTP error {status_code}: "
                f"{error.response.text[:300]}"
            ) from error

        except requests.exceptions.Timeout as error:

            raise RuntimeError(
                "OpenAQ request timed out after retries"
            ) from error

        except requests.exceptions.ConnectionError as error:

            raise RuntimeError(
                "Unable to connect to OpenAQ after retries. "
                "Check internet connectivity or API availability."
            ) from error

        except requests.exceptions.RequestException as error:

            raise RuntimeError(
                f"OpenAQ request failed: {error}"
            ) from error

    # --------------------------------------------------
    # FETCH SENSOR METADATA
    # --------------------------------------------------

    def get_sensors(self, location_id):

        return self._get(
            f"/locations/{location_id}/sensors"
        )

    # --------------------------------------------------
    # FETCH LATEST MEASUREMENTS
    # --------------------------------------------------

    def get_latest_measurements(self, location_id):

        return self._get(
            f"/locations/{location_id}/latest"
        )

    # --------------------------------------------------
    # FETCH HISTORICAL SENSOR MEASUREMENTS
    # --------------------------------------------------

    def get_historical_measurements(
        self,
        sensor_id,
        datetime_from,
        datetime_to,
        limit=1000,
        max_pages=20
    ):
        """
        Retrieve paginated historical measurements
        for a specific OpenAQ sensor.

        Parameters
        ----------
        sensor_id : int
            OpenAQ sensor ID.

        datetime_from : str
            Start timestamp in ISO 8601 format.

        datetime_to : str
            End timestamp in ISO 8601 format.

        limit : int
            Maximum records requested per page.

        max_pages : int
            Maximum number of pages to retrieve.

        Returns
        -------
        list
            Historical measurement records.
        """

        # Validate input parameters.
        if not isinstance(sensor_id, int) or sensor_id <= 0:
            raise ValueError("sensor_id must be a positive integer")

        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be a positive integer")

        # Validate ISO timestamps and timezone information.
        try:
            start_time = datetime.fromisoformat(
                datetime_from.replace("Z", "+00:00")
            )

            end_time = datetime.fromisoformat(
                datetime_to.replace("Z", "+00:00")
            )

        except (AttributeError, ValueError) as error:
            raise ValueError(
                "datetime_from and datetime_to must be valid ISO timestamps"
            ) from error

        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError(
                "Historical timestamps must include timezone information"
            )

        if start_time >= end_time:
            raise ValueError(
                "datetime_from must be earlier than datetime_to"
            )

        if not API_KEY:
            raise RuntimeError(
                "OPENAQ_API_KEY is not configured. Add it to the backend .env "
                "file or hosting environment variables."
            )

        records = []
        page = 1

        while page <= max_pages:

            url = (
                f"{BASE_URL}/sensors/"
                f"{sensor_id}/measurements"
            )

            params = {
                "datetime_from": datetime_from,
                "datetime_to": datetime_to,
                "limit": limit,
                "page": page
            }

            try:

                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )

                response.raise_for_status()

                try:
                    data = response.json()

                except requests.exceptions.JSONDecodeError as error:
                    raise RuntimeError(
                        f"Invalid JSON response for sensor "
                        f"{sensor_id}, page {page}"
                    ) from error

                if not isinstance(data, dict):
                    raise RuntimeError(
                        "Unexpected OpenAQ historical response format"
                    )

                page_records = data.get("results", [])

                if not isinstance(page_records, list):
                    raise RuntimeError(
                        "Unexpected OpenAQ historical results format"
                    )

                if not page_records:
                    break

                records.extend(page_records)

                print(
                    f"Sensor {sensor_id} | "
                    f"Page {page} | "
                    f"Records {len(page_records)} | "
                    f"Total {len(records)}"
                )

                # Stop when the API returns a partial page.
                if len(page_records) < limit:
                    break

                page += 1

            except requests.exceptions.HTTPError as error:

                status_code = error.response.status_code

                raise RuntimeError(
                    f"Historical OpenAQ HTTP error "
                    f"{status_code} for sensor {sensor_id}, "
                    f"page {page}: {error.response.text[:300]}"
                ) from error

            except requests.exceptions.Timeout as error:

                raise RuntimeError(
                    f"Historical request timed out for "
                    f"sensor {sensor_id}, page {page}"
                ) from error

            except requests.exceptions.ConnectionError as error:

                raise RuntimeError(
                    f"Connection failed for sensor "
                    f"{sensor_id}, page {page}"
                ) from error

            except requests.exceptions.RequestException as error:

                raise RuntimeError(
                    f"Historical retrieval failed for "
                    f"sensor {sensor_id}, page {page}: {error}"
                ) from error

        if page > max_pages and len(records) == limit * max_pages:
            print(
                f"WARNING: Maximum page limit ({max_pages}) reached. "
                "More records may be available."
            )

        return records

    # --------------------------------------------------
    # JOIN SENSOR METADATA + LATEST MEASUREMENTS
    # --------------------------------------------------

   
    def get_station_measurements(self, location_id):
        """
        Retrieve latest OpenAQ observations for a location.

        Returns validated sensor observations with:
        - pollutant and unit metadata
        - UTC timestamp
        - observation age
        - freshness classification

        This method does not treat stale observations as live.
        """

        if isinstance(location_id, bool) or not str(location_id).isdigit():
            raise ValueError("location_id must be a positive integer")

        location_id = int(location_id)

        if location_id <= 0:
            raise ValueError("location_id must be a positive integer")

        sensors = self.get_sensors(location_id)
        measurements = self.get_latest_measurements(location_id)

        sensor_lookup = {
            sensor["id"]: sensor
            for sensor in sensors
            if isinstance(sensor, dict) and sensor.get("id") is not None
        }

        now = datetime.now(timezone.utc)
        records = []

        for item in measurements:
            if not isinstance(item, dict):
                continue

            sensor_id = item.get("sensorsId")
            sensor = sensor_lookup.get(sensor_id)

            if not sensor:
                continue

            parameter = sensor.get("parameter") or {}
            datetime_info = item.get("datetime") or {}

            timestamp_string = datetime_info.get("utc")

            if not timestamp_string:
                continue

            try:
                timestamp = datetime.fromisoformat(
                    timestamp_string.replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                continue

            if timestamp.tzinfo is None:
                continue

            age_hours = (
                now - timestamp.astimezone(timezone.utc)
            ).total_seconds() / 3600

            # Reject timestamps that are unreasonably in the future.
            if age_hours < -1:
                continue

            value = item.get("value")

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            if not math.isfinite(value):
                continue

            if value < 0:
                continue

            if age_hours < 0:
                freshness = "invalid_future"
            elif age_hours <= 2:
                freshness = "FRESH"
            elif age_hours <= 24:
                freshness = "DELAYED"
            else:
                freshness = "STALE"

            records.append({
                "sensor_id": sensor_id,
                "pollutant": parameter.get("name"),
                "value": value,
                "unit": parameter.get("units"),
                "timestamp": timestamp.astimezone(
                    timezone.utc
                ).isoformat(),
                "age_hours": round(age_hours, 2),
                "freshness": freshness,
                "data_type": "ground_sensor_observation",
                "source": "OpenAQ"
            })

        # Keep the newest valid observation per sensor.
        newest_by_sensor = {}

        for record in records:
            sensor_id = record["sensor_id"]

            existing = newest_by_sensor.get(sensor_id)

            if (
                existing is None
                or record["timestamp"] > existing["timestamp"]
            ):
                newest_by_sensor[sensor_id] = record

        return list(newest_by_sensor.values())



# --------------------------------------------------
# SERVICE INSTANCE
# --------------------------------------------------

openaq_service = OpenAQService()

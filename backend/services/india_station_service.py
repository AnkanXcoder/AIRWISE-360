
import os
import logging
from typing import Any

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv()

logger = logging.getLogger(__name__)

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
LOCATIONS_ENDPOINT = f"{OPENAQ_BASE_URL}/locations"


# --------------------------------------------------
# INDIA STATION SERVICE
# --------------------------------------------------

class IndiaStationService:

    def __init__(self):

        self.api_key = os.getenv("OPENAQ_API_KEY")

        self.session = requests.Session()

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1,
            status_forcelist=[
                429, 500, 502, 503, 504
            ],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )

        adapter = HTTPAdapter(max_retries=retry)

        self.session.mount("https://", adapter)

        self.session.headers.update({
            "X-API-Key": self.api_key or "",
            "Accept": "application/json"
        })

    # --------------------------------------------------
    # TIMESTAMP NORMALIZATION
    # --------------------------------------------------

    @staticmethod
    def extract_timestamp(value):

        if isinstance(value, dict):

            return (
                value.get("utc")
                or value.get("local")
            )

        if isinstance(value, str):
            return value

        return None

    # --------------------------------------------------
    # LOCATION NORMALIZATION
    # --------------------------------------------------

    @staticmethod
    def normalize_location(
        location: dict[str, Any]
    ) -> dict:

        coordinates = location.get("coordinates") or {}
        country = location.get("country") or {}

        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        # Validate coordinates
        try:
            latitude = (
                float(latitude)
                if latitude is not None
                else None
            )

            longitude = (
                float(longitude)
                if longitude is not None
                else None
            )

            if latitude is not None and not -90 <= latitude <= 90:
                latitude = None

            if longitude is not None and not -180 <= longitude <= 180:
                longitude = None

        except (ValueError, TypeError):
            latitude = None
            longitude = None

        # Normalize supported pollutants
        parameters = location.get("parameters") or []

        normalized_parameters = []

        for parameter in parameters:

            if isinstance(parameter, dict):

                normalized_parameters.append({
                    "id": parameter.get("id"),
                    "name": parameter.get("name"),
                    "units": parameter.get("units"),
                    "display_name": parameter.get("displayName")
                })

        return {

            "source": "OpenAQ",

            "source_location_id": location.get("id"),

            "station_name": location.get("name"),

            "locality": location.get("locality"),

            "state": location.get("state"),

            "city": location.get("city"),

            "country": country.get("name"),

            "country_code": country.get("code"),

            "latitude": latitude,

            "longitude": longitude,

            "timezone": location.get("timezone"),

            "is_monitor": location.get("isMonitor"),

            "is_mobile": location.get("isMobile"),

            "first_observed": (
                IndiaStationService.extract_timestamp(
                    location.get("datetimeFirst")
                )
            ),

            "last_observed": (
                IndiaStationService.extract_timestamp(
                    location.get("datetimeLast")
                )
            ),

            "parameters": normalized_parameters
        }

    # --------------------------------------------------
    # INDIA-WIDE LOCATION DISCOVERY
    # --------------------------------------------------

    def discover_india_stations(
        self,
        limit: int = 1000,
        max_pages: int = 100
    ) -> dict:

        if not self.api_key:

            raise RuntimeError(
                "OPENAQ_API_KEY is missing from the project .env file."
            )

        if not 1 <= limit <= 1000:

            raise ValueError(
                "limit must be between 1 and 1000."
            )

        if max_pages < 1:

            raise ValueError(
                "max_pages must be at least 1."
            )

        all_locations = {}

        pages_fetched = 0

        # Fetch paginated India locations
        for page in range(1, max_pages + 1):

            params = {

                "iso": "IN",

                "limit": limit,

                "page": page,

                "order_by": "id",

                "sort_order": "asc"
            }

            try:

                response = self.session.get(

                    LOCATIONS_ENDPOINT,

                    params=params,

                    timeout=30
                )

                response.raise_for_status()

                payload = response.json()

            except requests.RequestException as error:

                logger.exception(
                    "OpenAQ discovery failed on page %s",
                    page
                )

                raise RuntimeError(
                    f"OpenAQ request failed on page {page}: {error}"
                ) from error

            except ValueError as error:

                raise RuntimeError(
                    "OpenAQ returned invalid JSON."
                ) from error

            results = payload.get("results", [])

            if not isinstance(results, list):

                raise RuntimeError(
                    "Unexpected OpenAQ response: results is not a list."
                )

            pages_fetched += 1

            if not results:
                break

            for location in results:

                location_id = location.get("id")

                if location_id is None:
                    continue

                normalized = self.normalize_location(location)

                all_locations[int(location_id)] = normalized

            logger.info(
                "Fetched OpenAQ page %s: %s locations",
                page,
                len(results)
            )

            if len(results) < limit:
                break

        stations = list(all_locations.values())

        # Geolocated stations
        geolocated = [

            station

            for station in stations

            if station["latitude"] is not None

            and station["longitude"] is not None
        ]

        # Unique states and cities where provided
        states = sorted({

            station["state"]

            for station in stations

            if station.get("state")
        })

        cities = sorted({

            station["city"]

            for station in stations

            if station.get("city")
        })

        return {

            "status": "success",

            "source": "OpenAQ",

            "country": "India",

            "country_code": "IN",

            "pages_fetched": pages_fetched,

            "total_locations_discovered": len(stations),

            "geolocated_locations": len(geolocated),

            "locations_without_coordinates": (
                len(stations) - len(geolocated)
            ),

            "states_available": len(states),

            "cities_available": len(cities),

            "stations": stations
        }


# --------------------------------------------------
# SERVICE INSTANCE
# --------------------------------------------------

india_station_service = IndiaStationService()


import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


DB_PATH = Path("data/airwise.db")

# Nominatim public service configuration.
GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
GEOCODING_USER_AGENT = "AIRWISE360-AirQualityIntelligence/1.0"
GEOCODING_TIMEOUT = 15

# Keep batches small when using the public Nominatim service.
MAX_GEOCODING_BATCH = 10
GEOCODING_REQUEST_INTERVAL = 1.1


class IndiaRegistryService:

    def __init__(self, db_path=DB_PATH):

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": GEOCODING_USER_AGENT
        })

        self._last_geocoding_request = 0.0

    # --------------------------------------------------
    # UTILITIES
    # --------------------------------------------------

    @staticmethod
    def _now_utc():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clean_text(value):
        if value is None:
            return None

        value = str(value).strip()

        return value if value else None

    @staticmethod
    def _with_display_geography(station):
        """Add honest display fields without relabelling a district as a city."""
        city = (station.get("city") or "").strip() or None
        district = (station.get("district") or "").strip() or None
        state = (station.get("state") or "").strip() or None

        if city:
            display_area = city
            location_level = "city"
            location_label = city
        elif district:
            display_area = district
            location_level = "district"
            location_label = f"{district}, {state}" if state else district
        elif state:
            display_area = state
            location_level = "state"
            location_label = state
        else:
            display_area = None
            location_level = "unknown"
            location_label = "Location details unavailable"

        station["display_city"] = city
        station["city_verified"] = bool(city)
        station["display_area"] = display_area
        station["location_level"] = location_level
        station["location_label"] = location_label
        station["geography_status"] = (
            "city_verified" if city else
            "district_fallback" if district else
            "state_fallback" if state else
            "unavailable"
        )
        return station

    @staticmethod
    def _to_bool_int(value):

        if value is None:
            return None

        if isinstance(value, str):
            return int(
                value.strip().lower()
                in {"1", "true", "yes", "y"}
            )

        return int(bool(value))

    @staticmethod
    def _valid_india_coordinates(latitude, longitude):

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return False

        return (
            5.0 <= latitude <= 37.5
            and 67.0 <= longitude <= 98.5
            and not (
                latitude == 0 and longitude == 0
            )
        )

    # --------------------------------------------------
    # CREATE TABLES AND INDEXES
    # --------------------------------------------------

    def create_table(self):

        with sqlite3.connect(self.db_path) as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS india_station_registry (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source TEXT NOT NULL,

                    source_location_id INTEGER NOT NULL,

                    station_name TEXT,

                    locality TEXT,

                    city TEXT,

                    district TEXT,

                    state TEXT,

                    country TEXT,

                    country_code TEXT,

                    latitude REAL,

                    longitude REAL,

                    timezone TEXT,

                    is_monitor INTEGER,

                    is_mobile INTEGER,

                    first_observed TEXT,

                    last_observed TEXT,

                    parameters_json TEXT,

                    discovered_at TEXT NOT NULL,

                    geographic_source TEXT,

                    geographic_enriched_at TEXT,

                    UNIQUE(source, source_location_id)
                )
            """)

            # Migrate existing databases without deleting data.

            existing_columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(india_station_registry)"
                ).fetchall()
            }

            migrations = {
                "district": "TEXT",
                "geographic_source": "TEXT",
                "geographic_enriched_at": "TEXT"
            }

            for column, definition in migrations.items():

                if column not in existing_columns:

                    conn.execute(
                        f"""
                        ALTER TABLE india_station_registry
                        ADD COLUMN {column} {definition}
                        """
                    )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_india_station_state_city

                ON india_station_registry(state, city)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_india_station_coordinates

                ON india_station_registry(latitude, longitude)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_india_station_name

                ON india_station_registry(station_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_india_station_geography

                ON india_station_registry(district, state)
            """)

            conn.commit()

    # --------------------------------------------------
    # SAVE / UPDATE STATIONS
    # --------------------------------------------------

    def save_stations(self, stations):

        self.create_table()

        saved = 0
        now = self._now_utc()

        with sqlite3.connect(self.db_path) as conn:

            for station in stations:

                location_id = station.get(
                    "source_location_id"
                )

                if location_id is None:
                    continue

                source = self._clean_text(
                    station.get("source")
                )

                if not source:
                    continue

                try:
                    location_id = int(location_id)
                except (TypeError, ValueError):
                    continue

                is_monitor = self._to_bool_int(
                    station.get("is_monitor")
                )

                is_mobile = self._to_bool_int(
                    station.get("is_mobile")
                )

                parameters = station.get("parameters", [])

                if not isinstance(parameters, list):
                    parameters = []

                latitude = station.get("latitude")
                longitude = station.get("longitude")

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
                except (TypeError, ValueError):
                    latitude = None
                    longitude = None

                conn.execute("""
                    INSERT INTO india_station_registry (

                        source,
                        source_location_id,
                        station_name,
                        locality,
                        city,
                        district,
                        state,
                        country,
                        country_code,
                        latitude,
                        longitude,
                        timezone,
                        is_monitor,
                        is_mobile,
                        first_observed,
                        last_observed,
                        parameters_json,
                        discovered_at,
                        geographic_source,
                        geographic_enriched_at

                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )

                    ON CONFLICT(source, source_location_id)

                    DO UPDATE SET

                        station_name =
                            COALESCE(
                                excluded.station_name,
                                india_station_registry.station_name
                            ),

                        locality =
                            COALESCE(
                                excluded.locality,
                                india_station_registry.locality
                            ),

                        city =
                            COALESCE(
                                NULLIF(excluded.city, ''),
                                india_station_registry.city
                            ),

                        district =
                            COALESCE(
                                NULLIF(excluded.district, ''),
                                india_station_registry.district
                            ),

                        state =
                            COALESCE(
                                NULLIF(excluded.state, ''),
                                india_station_registry.state
                            ),

                        country =
                            COALESCE(
                                excluded.country,
                                india_station_registry.country
                            ),

                        country_code =
                            COALESCE(
                                excluded.country_code,
                                india_station_registry.country_code
                            ),

                        latitude =
                            COALESCE(
                                excluded.latitude,
                                india_station_registry.latitude
                            ),

                        longitude =
                            COALESCE(
                                excluded.longitude,
                                india_station_registry.longitude
                            ),

                        timezone =
                            COALESCE(
                                excluded.timezone,
                                india_station_registry.timezone
                            ),

                        is_monitor =
                            COALESCE(
                                excluded.is_monitor,
                                india_station_registry.is_monitor
                            ),

                        is_mobile =
                            COALESCE(
                                excluded.is_mobile,
                                india_station_registry.is_mobile
                            ),

                        first_observed =
                            COALESCE(
                                excluded.first_observed,
                                india_station_registry.first_observed
                            ),

                        last_observed =
                            COALESCE(
                                excluded.last_observed,
                                india_station_registry.last_observed
                            ),

                        parameters_json =
                            CASE
                                WHEN excluded.parameters_json != '[]'
                                THEN excluded.parameters_json
                                ELSE india_station_registry.parameters_json
                            END,

                        discovered_at = excluded.discovered_at,

                        geographic_source =
                            COALESCE(
                                india_station_registry.geographic_source,
                                excluded.geographic_source
                            ),

                        geographic_enriched_at =
                            COALESCE(
                                india_station_registry.geographic_enriched_at,
                                excluded.geographic_enriched_at
                            )

                """, (

                    source,
                    location_id,

                    self._clean_text(
                        station.get("station_name")
                    ),

                    self._clean_text(
                        station.get("locality")
                    ),

                    self._clean_text(
                        station.get("city")
                    ),

                    self._clean_text(
                        station.get("district")
                    ),

                    self._clean_text(
                        station.get("state")
                    ),

                    self._clean_text(
                        station.get("country")
                    ),

                    self._clean_text(
                        station.get("country_code")
                    ),

                    latitude,
                    longitude,

                    self._clean_text(
                        station.get("timezone")
                    ),

                    is_monitor,
                    is_mobile,

                    station.get("first_observed"),
                    station.get("last_observed"),

                    json.dumps(parameters),

                    now,

                    station.get("geographic_source"),
                    station.get("geographic_enriched_at")

                ))

                saved += 1

            conn.commit()

        return saved

    # --------------------------------------------------
    # NATIONAL STATION SUMMARY
    # --------------------------------------------------

    def get_summary(self):

        self.create_table()

        with sqlite3.connect(self.db_path) as conn:

            total = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
            """).fetchone()[0]

            geolocated = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
            """).fetchone()[0]

            countries = conn.execute("""
                SELECT COUNT(DISTINCT country_code)
                FROM india_station_registry
                WHERE country_code IS NOT NULL
            """).fetchone()[0]

            monitors = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE is_monitor = 1
            """).fetchone()[0]

            mobile = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE is_mobile = 1
            """).fetchone()[0]

            with_city = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE city IS NOT NULL
                  AND TRIM(city) != ''
            """).fetchone()[0]

            with_district = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE district IS NOT NULL
                  AND TRIM(district) != ''
            """).fetchone()[0]

            with_state = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE state IS NOT NULL
                  AND TRIM(state) != ''
            """).fetchone()[0]

        return {
            "total_locations": total,
            "geolocated_locations": geolocated,
            "countries": countries,
            "monitor_locations": monitors,
            "mobile_locations": mobile,
            "locations_with_city": with_city,
            "locations_with_district": with_district,
            "locations_with_state": with_state
        }

    # --------------------------------------------------
    # SINGLE STATION LOOKUP
    # --------------------------------------------------

    def get_station(self, source, source_location_id):
        """Return one registered station using its source-scoped ID."""
        self.create_table()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM india_station_registry
                WHERE LOWER(source) = LOWER(?)
                  AND source_location_id = ?
                LIMIT 1
                """,
                (str(source).strip(), int(source_location_id))
            ).fetchone()

        if row is None:
            return None

        station = dict(row)
        try:
            station["parameters"] = json.loads(
                station.pop("parameters_json") or "[]"
            )
        except (ValueError, TypeError):
            station["parameters"] = []
        return self._with_display_geography(station)

    # --------------------------------------------------
    # PAGINATED STATION RETRIEVAL
    # --------------------------------------------------

    def get_stations(
        self,
        page=1,
        limit=100,
        search=None,
        state=None,
        city=None,
        district=None
    ):

        if page < 1:
            raise ValueError("Page must be at least 1.")

        if not 1 <= limit <= 1000:
            raise ValueError(
                "Limit must be between 1 and 1000."
            )

        self.create_table()

        conditions = []
        values = []

        if search:

            conditions.append("""
                (
                    station_name LIKE ?
                    OR locality LIKE ?
                    OR city LIKE ?
                    OR district LIKE ?
                    OR state LIKE ?
                )
            """)

            search_value = f"%{search}%"

            values.extend([
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ])

        if state:
            conditions.append("LOWER(TRIM(state)) = LOWER(TRIM(?))")
            values.append(state)

        if city:
            conditions.append("LOWER(TRIM(city)) = LOWER(TRIM(?))")
            values.append(city)

        if district:
            conditions.append("LOWER(TRIM(district)) = LOWER(TRIM(?))")
            values.append(district)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions
            else ""
        )

        offset = (page - 1) * limit

        with sqlite3.connect(self.db_path) as conn:

            conn.row_factory = sqlite3.Row

            total = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM india_station_registry
                {where_clause}
                """,
                values
            ).fetchone()[0]

            rows = conn.execute(
                f"""
                SELECT *
                FROM india_station_registry
                {where_clause}
                ORDER BY station_name
                LIMIT ? OFFSET ?
                """,
                values + [limit, offset]
            ).fetchall()

        stations = []

        for row in rows:

            station = dict(row)

            try:
                station["parameters"] = json.loads(
                    station.pop("parameters_json") or "[]"
                )
            except (ValueError, TypeError):
                station["parameters"] = []

            stations.append(self._with_display_geography(station))

        total_pages = (
            (total + limit - 1) // limit
        )

        return {
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "stations": stations
        }

    # --------------------------------------------------
    # STATE AND CITY FILTERS
    # --------------------------------------------------

    def get_geographic_filters(self):
        """Return separate administrative levels and honest display fallbacks."""
        self.create_table()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            states = conn.execute("""
                SELECT DISTINCT TRIM(state)
                FROM india_station_registry
                WHERE state IS NOT NULL AND TRIM(state) != ''
                ORDER BY TRIM(state) COLLATE NOCASE
            """).fetchall()

            cities = conn.execute("""
                SELECT DISTINCT TRIM(city)
                FROM india_station_registry
                WHERE city IS NOT NULL AND TRIM(city) != ''
                ORDER BY TRIM(city) COLLATE NOCASE
            """).fetchall()

            districts = conn.execute("""
                SELECT DISTINCT TRIM(district)
                FROM india_station_registry
                WHERE district IS NOT NULL AND TRIM(district) != ''
                ORDER BY TRIM(district) COLLATE NOCASE
            """).fetchall()

            location_rows = conn.execute("""
                SELECT
                    CASE
                        WHEN city IS NOT NULL AND TRIM(city) != '' THEN TRIM(city)
                        WHEN district IS NOT NULL AND TRIM(district) != '' THEN TRIM(district)
                        WHEN state IS NOT NULL AND TRIM(state) != '' THEN TRIM(state)
                        ELSE 'Location details unavailable'
                    END AS display_area,
                    CASE
                        WHEN city IS NOT NULL AND TRIM(city) != '' THEN 'city'
                        WHEN district IS NOT NULL AND TRIM(district) != '' THEN 'district'
                        WHEN state IS NOT NULL AND TRIM(state) != '' THEN 'state'
                        ELSE 'unknown'
                    END AS location_level,
                    TRIM(state) AS state,
                    TRIM(district) AS district,
                    TRIM(city) AS city,
                    COUNT(*) AS station_count
                FROM india_station_registry
                GROUP BY display_area, location_level, state, district, city
                ORDER BY state COLLATE NOCASE, display_area COLLATE NOCASE
            """).fetchall()

            coverage = conn.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN city IS NOT NULL AND TRIM(city) != '' THEN 1 ELSE 0 END) AS city_count,
                    SUM(CASE WHEN (city IS NULL OR TRIM(city) = '') AND district IS NOT NULL AND TRIM(district) != '' THEN 1 ELSE 0 END) AS district_fallback_count,
                    SUM(CASE WHEN (city IS NULL OR TRIM(city) = '') AND (district IS NULL OR TRIM(district) = '') AND state IS NOT NULL AND TRIM(state) != '' THEN 1 ELSE 0 END) AS state_fallback_count
                FROM india_station_registry
            """).fetchone()

        location_options = []
        for row in location_rows:
            item = dict(row)
            item["label"] = (
                f"{item['display_area']}, {item['state']}"
                if item.get("state") and item["display_area"] != item["state"]
                else item["display_area"]
            )
            location_options.append(item)

        return {
            "states": [row[0] for row in states],
            "cities": [row[0] for row in cities],
            "districts": [row[0] for row in districts],
            "location_options": location_options,
            "coverage": {
                "total_locations": coverage[0] or 0,
                "verified_city_locations": coverage[1] or 0,
                "district_fallback_locations": coverage[2] or 0,
                "state_fallback_locations": coverage[3] or 0
            },
            "location_policy": "Use verified city when available; otherwise display district and state without labelling the district as a city."
        }

    # --------------------------------------------------
    # GEOGRAPHIC MAP DATA
    # --------------------------------------------------

    def get_map_stations(self, limit=1000):

        if not 1 <= limit <= 10000:
            raise ValueError(
                "Map limit must be between 1 and 10000."
            )

        self.create_table()

        with sqlite3.connect(self.db_path) as conn:

            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT
                    source,
                    source_location_id,
                    station_name,
                    locality,
                    city,
                    district,
                    state,
                    country,
                    country_code,
                    latitude,
                    longitude,
                    is_monitor,
                    is_mobile,
                    geographic_source,
                    geographic_enriched_at

                FROM india_station_registry

                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL

                ORDER BY station_name

                LIMIT ?
            """, (limit,)).fetchall()

        return {
            "status": "success",
            "total": len(rows),
            "stations": [
                self._with_display_geography(dict(row))
                for row in rows
            ]
        }

    # --------------------------------------------------
    # REVERSE GEOCODING
    # --------------------------------------------------

    def reverse_geocode(self, latitude, longitude):

        if not self._valid_india_coordinates(
            latitude,
            longitude
        ):
            return None

        params = {
            "lat": float(latitude),
            "lon": float(longitude),
            "format": "jsonv2",
            "addressdetails": 1
        }

        try:

            response = self.session.get(
                GEOCODING_URL,
                params=params,
                timeout=GEOCODING_TIMEOUT
            )

            response.raise_for_status()

            result = response.json()

            address = result.get("address", {})

            if not isinstance(address, dict):
                return None

            city = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or address.get("city_district")
                or address.get("suburb")
            )

            district = (
                address.get("state_district")
                or address.get("county")
            )

            state = address.get("state")

            return {
                "city": self._clean_text(city),
                "district": self._clean_text(district),
                "state": self._clean_text(state),
                "source": "OpenStreetMap Nominatim"
            }

        except requests.RequestException as error:

            print(
                f"Geocoding request failed "
                f"for {latitude}, {longitude}: {error}"
            )

            return None

        except (ValueError, TypeError, AttributeError) as error:

            print(f"Geocoding response error: {error}")

            return None

    # --------------------------------------------------
    # ENRICH MISSING GEOGRAPHIC METADATA
    # --------------------------------------------------

    def enrich_missing_geography(self, limit=5):

        """
        Enrich missing city, district and state fields.

        Uses OpenStreetMap Nominatim reverse geocoding.
        Processes a small batch to respect its public
        service usage restrictions.

        Run this method periodically, not on every API request.
        """

        if not 1 <= limit <= MAX_GEOCODING_BATCH:
            raise ValueError(
                f"Limit must be between 1 and "
                f"{MAX_GEOCODING_BATCH}."
            )

        self.create_table()

        with sqlite3.connect(self.db_path) as conn:

            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT
                    id,
                    source,
                    source_location_id,
                    station_name,
                    latitude,
                    longitude,
                    city,
                    district,
                    state

                FROM india_station_registry

                WHERE
                    latitude IS NOT NULL
                    AND longitude IS NOT NULL

                    AND latitude BETWEEN 5 AND 37.5
                    AND longitude BETWEEN 67 AND 98.5

                    AND (
                        city IS NULL OR TRIM(city) = ''
                        OR district IS NULL OR TRIM(district) = ''
                        OR state IS NULL OR TRIM(state) = ''
                    )

                ORDER BY id

                LIMIT ?
            """, (limit,)).fetchall()

        processed = 0
        enriched = 0
        failed = 0

        for station in rows:

            # Enforce the public Nominatim request interval.
            elapsed = (
                time.monotonic()
                - self._last_geocoding_request
            )

            wait_time = (
                GEOCODING_REQUEST_INTERVAL - elapsed
            )

            if wait_time > 0:
                time.sleep(wait_time)

            self._last_geocoding_request = time.monotonic()

            processed += 1

            result = self.reverse_geocode(
                station["latitude"],
                station["longitude"]
            )

            if not result:
                failed += 1
                continue

            # Never overwrite existing non-empty metadata.
            city = (
                station["city"]
                or result["city"]
            )

            district = (
                station["district"]
                or result["district"]
            )

            state = (
                station["state"]
                or result["state"]
            )

            # Do not claim successful enrichment if the
            # provider did not return any useful geography.
            if not any([city, district, state]):
                failed += 1
                continue

            enriched_at = self._now_utc()

            with sqlite3.connect(self.db_path) as conn:

                conn.execute("""
                    UPDATE india_station_registry

                    SET
                        city = ?,
                        district = ?,
                        state = ?,
                        geographic_source = ?,
                        geographic_enriched_at = ?

                    WHERE id = ?
                """, (
                    city,
                    district,
                    state,
                    result["source"],
                    enriched_at,
                    station["id"]
                ))

                conn.commit()

            enriched += 1

        with sqlite3.connect(self.db_path) as conn:

            remaining = conn.execute("""
                SELECT COUNT(*)

                FROM india_station_registry

                WHERE
                    latitude IS NOT NULL
                    AND longitude IS NOT NULL

                    AND latitude BETWEEN 5 AND 37.5
                    AND longitude BETWEEN 67 AND 98.5

                    AND (
                        city IS NULL OR TRIM(city) = ''
                        OR district IS NULL OR TRIM(district) = ''
                        OR state IS NULL OR TRIM(state) = ''
                    )
            """).fetchone()[0]

        return {
            "status": "success",
            "requested_limit": limit,
            "processed": processed,
            "enriched": enriched,
            "failed": failed,
            "remaining_locations": remaining,
            "geographic_source": "OpenStreetMap Nominatim"
        }

    # --------------------------------------------------
    # GEOGRAPHIC ENRICHMENT SUMMARY
    # --------------------------------------------------

    def get_geography_summary(self):

        self.create_table()

        with sqlite3.connect(self.db_path) as conn:

            total = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
            """).fetchone()[0]

            with_coordinates = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
            """).fetchone()[0]

            with_city = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE city IS NOT NULL
                  AND TRIM(city) != ''
            """).fetchone()[0]

            with_district = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE district IS NOT NULL
                  AND TRIM(district) != ''
            """).fetchone()[0]

            with_state = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE state IS NOT NULL
                  AND TRIM(state) != ''
            """).fetchone()[0]

            enriched = conn.execute("""
                SELECT COUNT(*)
                FROM india_station_registry
                WHERE geographic_enriched_at IS NOT NULL
            """).fetchone()[0]

        return {
            "total_locations": total,
            "with_coordinates": with_coordinates,
            "with_city": with_city,
            "with_district": with_district,
            "with_state": with_state,
            "geographically_enriched": enriched,
            "geographic_source": "OpenStreetMap Nominatim"
        }


# --------------------------------------------------
# SERVICE INSTANCE
# --------------------------------------------------

india_registry_service = IndiaRegistryService()

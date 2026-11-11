
import sqlite3
from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Database storage location
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "airwise.db"


def get_connection():
    """Create a connection to the AIRWISE SQLite database."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """Create the historical measurements table."""

    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS air_quality_measurements (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                location_id INTEGER NOT NULL,

                station_name TEXT,

                pollutant TEXT NOT NULL,

                sensor_id INTEGER NOT NULL,

                value REAL,

                unit TEXT,

                observed_at TEXT NOT NULL,

                retrieved_at TEXT NOT NULL,

                freshness TEXT,

                source TEXT NOT NULL,

                UNIQUE(sensor_id, observed_at)

            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_pollutant_observed
            ON air_quality_measurements (
                pollutant,
                observed_at
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_location_observed
            ON air_quality_measurements (
                location_id,
                observed_at
            )
        """)

        connection.commit()

    finally:
        connection.close()


def save_measurements(
    records,
    location_id,
    station_name,
    retrieved_at,
    source="OpenAQ"
):
    """Insert new measurements or update existing observations."""

    connection = get_connection()

    try:
        query = """
            INSERT INTO air_quality_measurements (
                location_id,
                station_name,
                pollutant,
                sensor_id,
                value,
                unit,
                observed_at,
                retrieved_at,
                freshness,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(sensor_id, observed_at)
            DO UPDATE SET
                value = excluded.value,
                unit = excluded.unit,
                retrieved_at = excluded.retrieved_at,
                freshness = excluded.freshness
        """

        values = [
            (
                location_id,
                station_name,
                record.get("pollutant"),
                record.get("sensor_id"),
                record.get("value"),
                record.get("unit"),
                record.get("timestamp"),
                retrieved_at,
                record.get("freshness"),
                source
            )
            for record in records
            if record.get("pollutant")
            and record.get("sensor_id") is not None
            and record.get("timestamp")
        ]

        connection.executemany(query, values)
        connection.commit()

        return len(values)

    finally:
        connection.close()


def get_measurement_count():
    """Return the total number of stored observations."""

    connection = get_connection()

    try:
        result = connection.execute("""
            SELECT COUNT(*) AS total
            FROM air_quality_measurements
        """).fetchone()

        return result["total"]

    finally:
        connection.close()



def get_historical_measurements(
    location_id,
    pollutant,
    limit=100
):
    """Retrieve historical observations for a station and pollutant."""

    connection = get_connection()

    try:
        query = """
            SELECT
                location_id,
                station_name,
                pollutant,
                sensor_id,
                value,
                unit,
                observed_at,
                retrieved_at,
                freshness,
                source

            FROM air_quality_measurements

            WHERE location_id = ?
            AND pollutant = ?

            ORDER BY observed_at DESC

            LIMIT ?
        """

        results = connection.execute(
            query,
            (location_id, pollutant, limit)
        ).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()


import sys
from datetime import datetime, timezone

from backend.services.openaq_service import openaq_service
from backend.database import get_connection

from backend.ingestion.historical_ingestion import (
    LOCATION_ID,
    STATION_NAME,
    POLLUTANT,
    PAGE_LIMIT,
    MAX_PAGES,
    get_date_range,
    get_pm25_sensors,
    validate_record,
    has_quality_flag,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SOURCE = "OpenAQ historical"


# --------------------------------------------------
# FETCH HISTORICAL DATA
# --------------------------------------------------

def fetch_historical_records():

    datetime_from, datetime_to = get_date_range()

    sensors = get_pm25_sensors()

    if not sensors:
        raise RuntimeError("No PM2.5 sensors found.")

    all_records = []

    print(f"PM2.5 sensors found: {len(sensors)}")

    for sensor in sensors:

        sensor_id = sensor.get("id")

        if not isinstance(sensor_id, int):
            continue

        print(f"\nFetching sensor: {sensor_id}")

        records = openaq_service.get_historical_measurements(
            sensor_id=sensor_id,
            datetime_from=datetime_from,
            datetime_to=datetime_to,
            limit=PAGE_LIMIT,
            max_pages=MAX_PAGES
        )

        for record in records:
            record["_sensor_id"] = sensor_id

        all_records.extend(records)

    return all_records, datetime_from, datetime_to


# --------------------------------------------------
# NORMALIZE AND VALIDATE
# --------------------------------------------------

def prepare_records(raw_records):

    valid_records = []
    rejected_count = 0
    flagged_count = 0
    duplicate_count = 0

    seen_keys = set()

    for raw in raw_records:

        normalized, status = validate_record(raw)

        if status != "valid":
            rejected_count += 1
            continue

        if has_quality_flag(raw):
            flagged_count += 1
            continue

        sensor_id = raw.get("_sensor_id")

        if not isinstance(sensor_id, int):
            rejected_count += 1
            continue

        normalized["sensor_id"] = sensor_id

        key = (
            sensor_id,
            normalized["timestamp"]
        )

        if key in seen_keys:
            duplicate_count += 1
            continue

        seen_keys.add(key)

        valid_records.append(normalized)

    return (
        valid_records,
        rejected_count,
        flagged_count,
        duplicate_count
    )


# --------------------------------------------------
# CHECK EXISTING DATABASE RECORDS
# --------------------------------------------------

def get_existing_keys(sensor_ids):

    if not sensor_ids:
        return set()

    placeholders = ",".join("?" for _ in sensor_ids)

    query = f"""
        SELECT sensor_id, observed_at
        FROM air_quality_measurements
        WHERE sensor_id IN ({placeholders})
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            query,
            tuple(sensor_ids)
        ).fetchall()

        return {
            (row["sensor_id"], row["observed_at"])
            for row in rows
        }

    finally:
        connection.close()


# --------------------------------------------------
# INSERT-ONLY DATABASE OPERATION
# --------------------------------------------------

def insert_new_records(records):

    retrieved_at = datetime.now(
        timezone.utc
    ).isoformat()

    query = """
        INSERT OR IGNORE INTO air_quality_measurements (
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
    """

    connection = get_connection()

    inserted_count = 0
    ignored_count = 0

    try:

        with connection:

            for record in records:

                cursor = connection.execute(
                    query,
                    (
                        LOCATION_ID,
                        STATION_NAME,
                        record["pollutant"],
                        record["sensor_id"],
                        record["value"],
                        record["unit"],
                        record["timestamp"],
                        retrieved_at,
                        None,
                        SOURCE
                    )
                )

                if cursor.rowcount == 1:
                    inserted_count += 1
                else:
                    ignored_count += 1

        return inserted_count, ignored_count

    finally:
        connection.close()


# --------------------------------------------------
# MAIN INGESTION WORKFLOW
# --------------------------------------------------

def run_ingestion(commit=False):

    print("\n" + "=" * 60)
    print("AIRWISE 360 - HISTORICAL DATA INGESTION")
    print("=" * 60)

    print(f"Station: {STATION_NAME}")
    print(f"Location ID: {LOCATION_ID}")
    print(f"Pollutant: {POLLUTANT}")

    if commit:
        print("MODE: COMMIT")
    else:
        print("MODE: DRY RUN")

    # Step 1: Fetch data.
    print("\n[1] Fetching historical data...")

    raw_records, date_from, date_to = (
        fetch_historical_records()
    )

    print(f"Date from: {date_from}")
    print(f"Date to: {date_to}")
    print(f"Raw records: {len(raw_records)}")

    # Step 2: Validate and normalize.
    print("\n[2] Validating records...")

    (
        valid_records,
        rejected_count,
        flagged_count,
        duplicate_count
    ) = prepare_records(raw_records)

    print(f"Valid records: {len(valid_records)}")
    print(f"Rejected records: {rejected_count}")
    print(f"Flagged records excluded: {flagged_count}")
    print(f"Duplicate API records: {duplicate_count}")

    # Step 3: Check database.
    print("\n[3] Checking existing database records...")

    sensor_ids = sorted({
        record["sensor_id"]
        for record in valid_records
    })

    existing_keys = get_existing_keys(sensor_ids)

    new_records = []

    for record in valid_records:

        key = (
            record["sensor_id"],
            record["timestamp"]
        )

        if key not in existing_keys:
            new_records.append(record)

    already_exists = (
        len(valid_records) - len(new_records)
    )

    print(f"Already existing: {already_exists}")
    print(f"New candidate records: {len(new_records)}")

    # Step 4: Insert only when explicitly requested.
    print("\n[4] Database operation")

    inserted_count = 0
    ignored_count = 0

    if commit:

        inserted_count, ignored_count = (
            insert_new_records(new_records)
        )

        print(f"Inserted records: {inserted_count}")
        print(f"Ignored records: {ignored_count}")

    else:

        print("DRY RUN: No database changes made.")
        print("To insert, run this script with --commit.")

    # Step 5: Final report.
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)

    print(f"Raw records: {len(raw_records)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Rejected records: {rejected_count}")
    print(f"Flagged records excluded: {flagged_count}")
    print(f"Duplicate API records: {duplicate_count}")
    print(f"Already in database: {already_exists}")
    print(f"New candidates: {len(new_records)}")
    print(f"Inserted: {inserted_count}")
    print(f"Ignored by SQLite: {ignored_count}")

    if commit:
        print("\nDATABASE STATUS: COMMIT COMPLETED")
    else:
        print("\nDATABASE STATUS: UNCHANGED")

    print("=" * 60)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    commit_requested = "--commit" in sys.argv

    run_ingestion(commit=commit_requested)

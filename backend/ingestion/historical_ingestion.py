
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from backend.services.openaq_service import openaq_service
from backend.database import get_connection


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

LOCATION_ID = 6950
STATION_NAME = "Jadavpur"

POLLUTANT = "pm25"

DAYS = 30

PAGE_LIMIT = 1000
MAX_PAGES = 20

# Report gaps longer than this threshold.
GAP_THRESHOLD_MINUTES = 60


# --------------------------------------------------
# DATE RANGE
# --------------------------------------------------

def get_date_range():

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=DAYS)

    return (
        start_time.isoformat().replace("+00:00", "Z"),
        end_time.isoformat().replace("+00:00", "Z")
    )


# --------------------------------------------------
# FETCH PM2.5 SENSORS
# --------------------------------------------------

def get_pm25_sensors():

    sensors = openaq_service.get_sensors(LOCATION_ID)

    return [
        sensor
        for sensor in sensors
        if (sensor.get("parameter") or {}).get(
            "name", ""
        ).lower() == POLLUTANT
    ]


# --------------------------------------------------
# VALIDATE HISTORICAL RECORD
# --------------------------------------------------

def validate_record(record):

    parameter = record.get("parameter") or {}
    period = record.get("period") or {}
    datetime_from = period.get("datetimeFrom") or {}

    pollutant = parameter.get("name")
    value = record.get("value")
    timestamp = datetime_from.get("utc")
    unit = parameter.get("units")

    if pollutant != POLLUTANT:
        return None, "wrong_pollutant"

    if not isinstance(value, (int, float)):
        return None, "invalid_value"

    if not math.isfinite(value):
        return None, "non_finite_value"

    if not timestamp:
        return None, "missing_timestamp"

    try:
        parsed_timestamp = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

    except (ValueError, AttributeError):
        return None, "invalid_timestamp"

    if parsed_timestamp.tzinfo is None:
        return None, "timezone_missing"

    if parsed_timestamp > datetime.now(timezone.utc):
        return None, "future_timestamp"

    if not unit:
        return None, "missing_unit"

    normalized = {
        "sensor_id": None,
        "pollutant": pollutant,
        "value": float(value),
        "unit": unit,
        "timestamp": parsed_timestamp.astimezone(
            timezone.utc
        ).isoformat(),
        "freshness": None
    }

    return normalized, "valid"


# --------------------------------------------------
# CHECK EXISTING DATABASE RECORDS
# --------------------------------------------------

def get_existing_keys():

    connection = get_connection()

    try:

        query = text("""
            SELECT sensor_id, observed_at
            FROM air_quality_measurements
            WHERE location_id = :location_id
            AND pollutant = :pollutant
        """)

        rows = connection.execute(
            query,
            {
                "location_id": LOCATION_ID,
                "pollutant": POLLUTANT
            }
        ).mappings().all()

        return {
            (row["sensor_id"], row["observed_at"])
            for row in rows
        }

    finally:
        connection.close()


# --------------------------------------------------
# QUALITY FLAG DETECTION
# --------------------------------------------------

def has_quality_flag(record):

    flag_info = record.get("flagInfo") or {}

    if isinstance(flag_info, dict):
        return bool(flag_info.get("hasFlags", False))

    return False


# --------------------------------------------------
# TEMPORAL COVERAGE ANALYSIS
# --------------------------------------------------

def analyze_temporal_coverage(records):

    grouped = defaultdict(list)

    for record in records:

        timestamp = datetime.fromisoformat(
            record["timestamp"].replace("Z", "+00:00")
        )

        grouped[record["sensor_id"]].append(timestamp)

    print("\nTEMPORAL COVERAGE BY SENSOR")
    print("-" * 60)

    for sensor_id, timestamps in sorted(grouped.items()):

        timestamps.sort()

        if len(timestamps) < 2:
            print(
                f"Sensor {sensor_id}: "
                f"Insufficient observations for interval analysis"
            )
            continue

        intervals = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() / 60
            for i in range(1, len(timestamps))
        ]

        median_interval = statistics.median(intervals)

        maximum_gap = max(intervals)

        large_gaps = sum(
            gap > GAP_THRESHOLD_MINUTES
            for gap in intervals
        )

        print(f"\nSensor ID: {sensor_id}")
        print(f"Observations: {len(timestamps)}")
        print(f"Earliest: {timestamps[0].isoformat()}")
        print(f"Latest: {timestamps[-1].isoformat()}")
        print(
            f"Median sampling interval: "
            f"{median_interval:.2f} minutes"
        )
        print(f"Maximum gap: {maximum_gap:.2f} minutes")
        print(
            f"Gaps greater than {GAP_THRESHOLD_MINUTES} minutes: "
            f"{large_gaps}"
        )


# --------------------------------------------------
# UNIT CONSISTENCY ANALYSIS
# --------------------------------------------------

def analyze_units(records):

    unit_counts = Counter(
        record["unit"]
        for record in records
    )

    print("\nUNIT DISTRIBUTION")
    print("-" * 60)

    for unit, count in unit_counts.items():
        print(f"{unit}: {count}")

    if len(unit_counts) > 1:
        print(
            "\nWARNING: Multiple units detected. "
            "Do not combine values until units are standardized."
        )

    elif len(unit_counts) == 1:
        print("\nOne consistent unit detected.")

    else:
        print("\nNo units available.")


# --------------------------------------------------
# SENSOR DISTRIBUTION ANALYSIS
# --------------------------------------------------

def analyze_sensor_distribution(records):

    sensor_counts = Counter(
        record["sensor_id"]
        for record in records
    )

    print("\nSENSOR DISTRIBUTION")
    print("-" * 60)

    for sensor_id, count in sorted(sensor_counts.items()):
        print(f"Sensor {sensor_id}: {count} observations")


# --------------------------------------------------
# QUALITY FLAG ANALYSIS
# --------------------------------------------------

def analyze_quality_flags(records):

    flagged_count = sum(
        has_quality_flag(record)
        for record in records
    )

    unflagged_count = len(records) - flagged_count

    print("\nOPENAQ QUALITY FLAGS")
    print("-" * 60)

    print(f"Flagged observations: {flagged_count}")
    print(f"Unflagged observations: {unflagged_count}")

    return flagged_count


# --------------------------------------------------
# DRY RUN INGESTION
# --------------------------------------------------

def run_dry_run():

    print("\n" + "=" * 60)
    print("AIRWISE 360 - HISTORICAL DATA QUALITY DRY RUN")
    print("=" * 60)

    datetime_from, datetime_to = get_date_range()

    print(f"\nStation       : {STATION_NAME}")
    print(f"Location ID   : {LOCATION_ID}")
    print(f"Pollutant     : {POLLUTANT}")
    print(f"Date From     : {datetime_from}")
    print(f"Date To       : {datetime_to}")

    # Step 1: Fetch sensors.
    print("\n[1] Fetching PM2.5 sensors...")

    sensors = get_pm25_sensors()

    print(f"PM2.5 sensors found: {len(sensors)}")

    if not sensors:
        print("No PM2.5 sensors found. Stopping.")
        return

    # Step 2: Fetch historical records.
    print("\n[2] Fetching historical measurements...")

    all_records = []

    for sensor in sensors:

        sensor_id = sensor.get("id")

        if not isinstance(sensor_id, int):
            print("Skipping sensor with invalid ID.")
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

    print(f"\nTotal API records: {len(all_records)}")

    # Step 3: Validate records.
    print("\n[3] Validating records...")

    valid_records = []
    rejected_counts = {}

    for record in all_records:

        normalized, status = validate_record(record)

        if status != "valid":

            rejected_counts[status] = (
                rejected_counts.get(status, 0) + 1
            )

            continue

        normalized["sensor_id"] = record["_sensor_id"]

        valid_records.append(normalized)

    print(f"Valid records: {len(valid_records)}")

    # Step 4: Detect duplicate API records.
    print("\n[4] Checking duplicate API records...")

    unique_records = []
    seen_keys = set()

    duplicate_api_count = 0

    for record in valid_records:

        key = (
            record["sensor_id"],
            record["timestamp"]
        )

        if key in seen_keys:
            duplicate_api_count += 1
            continue

        seen_keys.add(key)
        unique_records.append(record)

    print(f"Unique records: {len(unique_records)}")
    print(f"Duplicate API records: {duplicate_api_count}")

    # Step 5: Check database records.
    print("\n[5] Checking existing SQLite records...")

    existing_keys = get_existing_keys()

    new_records = []
    existing_count = 0

    for record in unique_records:

        key = (
            record["sensor_id"],
            record["timestamp"]
        )

        if key in existing_keys:
            existing_count += 1
        else:
            new_records.append(record)

    print(f"Already in database: {existing_count}")
    print(f"New candidate records: {len(new_records)}")

    # Step 6: Extended data quality analysis.
    print("\n[6] Running extended data quality analysis...")

    analyze_sensor_distribution(unique_records)

    analyze_temporal_coverage(unique_records)

    analyze_units(unique_records)

    flagged_count = analyze_quality_flags(all_records)

    # Step 7: Rejected records.
    print("\nREJECTED RECORD SUMMARY")
    print("-" * 60)

    if rejected_counts:

        for reason, count in sorted(rejected_counts.items()):
            print(f"{reason}: {count}")

    else:
        print("No rejected records.")

    # Step 8: Final report.
    print("\n" + "=" * 60)
    print("FINAL DRY RUN SUMMARY")
    print("=" * 60)

    print(f"Total API records       : {len(all_records)}")
    print(f"Valid records           : {len(valid_records)}")
    print(f"Unique valid records    : {len(unique_records)}")
    print(f"Duplicate API records   : {duplicate_api_count}")
    print(f"Existing DB records     : {existing_count}")
    print(f"New candidate records   : {len(new_records)}")
    print(f"Rejected records        : {sum(rejected_counts.values())}")
    print(f"Flagged observations    : {flagged_count}")

    print("\nDATABASE STATUS: UNCHANGED")
    print("No records were inserted or updated.")

    print("=" * 60)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    run_dry_run()

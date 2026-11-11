
from datetime import datetime, timezone


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

CORE_POLLUTANTS = {
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
}

FRESH_HOURS = 2
DELAYED_HOURS = 24


# --------------------------------------------------
# FRESHNESS CLASSIFICATION
# --------------------------------------------------

def classify_freshness(age_hours):

    if age_hours < 0:
        return "INVALID_FUTURE"

    elif age_hours <= FRESH_HOURS:
        return "FRESH"

    elif age_hours <= DELAYED_HOURS:
        return "DELAYED"

    return "STALE"


# --------------------------------------------------
# PROCESS MEASUREMENTS
# --------------------------------------------------

def process_measurements(records):

    now = datetime.now(timezone.utc)

    processed_records = []

    for record in records:

        timestamp = datetime.fromisoformat(
            record["timestamp"]
        )

        if timestamp.tzinfo is None:
            raise ValueError(
                "Measurement timestamp must include timezone information"
            )

        age_hours = (
            now - timestamp
        ).total_seconds() / 3600

        freshness = classify_freshness(age_hours)

        processed = {
            **record,
            "age_hours": round(age_hours, 2),
            "freshness": freshness
        }

        processed_records.append(processed)

    # --------------------------------------------------
    # SELECT CORE POLLUTANTS
    # --------------------------------------------------

    selected = {}

    for record in processed_records:

        pollutant = record.get("pollutant")

        if pollutant not in CORE_POLLUTANTS:
            continue

        if record["freshness"] in (
            "STALE",
            "INVALID_FUTURE"
        ):
            continue

        if record.get("value") is None:
            continue

        if pollutant not in selected:

            selected[pollutant] = record

        elif (
            record["timestamp"] >
            selected[pollutant]["timestamp"]
        ):

            selected[pollutant] = record

    # --------------------------------------------------
    # QUALITY SUMMARY
    # --------------------------------------------------

    summary = {
        "total_records": len(processed_records),

        "fresh": sum(
            r["freshness"] == "FRESH"
            for r in processed_records
        ),

        "delayed": sum(
            r["freshness"] == "DELAYED"
            for r in processed_records
        ),

        "stale": sum(
            r["freshness"] == "STALE"
            for r in processed_records
        ),

        "invalid_future": sum(
            r["freshness"] == "INVALID_FUTURE"
            for r in processed_records
        ),

        "expected_pollutants": len(CORE_POLLUTANTS),

        "available_pollutants": len(selected),

        "missing_pollutants": sorted(
            CORE_POLLUTANTS - set(selected)
        )
    }

    return {
        "records": processed_records,
        "selected_pollutants": selected,
        "summary": summary
    }

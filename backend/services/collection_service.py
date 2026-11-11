
from datetime import datetime, timezone

from backend.services.openaq_service import openaq_service
from backend.services.data_quality import process_measurements
from backend.database import save_measurements


def collect_station_data(location_id, station_name):
    """
    Fetch station observations, apply quality checks,
    and store the observations in SQLite.
    """

    print(f"\nCollecting data for {station_name}...")

    # Step 1: Fetch observations from OpenAQ
    records = openaq_service.get_station_measurements(location_id)

    if not records:
        raise RuntimeError("No sensor records returned by OpenAQ")

    # Step 2: Apply data quality checks
    result = process_measurements(records)

    # Step 3: Generate retrieval timestamp
    retrieved_at = datetime.now(timezone.utc).isoformat()

    # Step 4: Save observations in SQLite
    saved_count = save_measurements(
        records=result["records"],
        location_id=location_id,
        station_name=station_name,
        retrieved_at=retrieved_at,
        source="OpenAQ"
    )

    # Step 5: Return collection report
    return {
        "station_id": location_id,
        "station_name": station_name,
        "records_received": len(records),
        "records_processed": len(result["records"]),
        "records_submitted_to_database": saved_count,
        "quality_summary": result["summary"],
        "retrieved_at": retrieved_at
    }

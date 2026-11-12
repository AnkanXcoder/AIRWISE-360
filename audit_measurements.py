
from sqlalchemy import text
from backend.db_engine import engine, DATABASE_TYPE

print("DATABASE:", DATABASE_TYPE)

with engine.connect() as conn:

    # 1. Total records
    total = conn.execute(
        text("SELECT COUNT(*) FROM air_quality_measurements")
    ).scalar_one()

    # 2. Duplicate sensor-time combinations
    duplicates = conn.execute(text("""
        SELECT COUNT(*)
        FROM (
            SELECT sensor_id, observed_at
            FROM air_quality_measurements
            GROUP BY sensor_id, observed_at
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
    """)).scalar_one()

    # 3. Missing values
    missing_values = conn.execute(text("""
        SELECT COUNT(*)
        FROM air_quality_measurements
        WHERE value IS NULL
    """)).scalar_one()

    # 4. Pollutant distribution
    pollutant_counts = conn.execute(text("""
        SELECT pollutant, COUNT(*)
        FROM air_quality_measurements
        GROUP BY pollutant
        ORDER BY pollutant
    """)).fetchall()

    # 5. Date range
    date_range = conn.execute(text("""
        SELECT MIN(observed_at), MAX(observed_at)
        FROM air_quality_measurements
    """)).fetchone()

print("\n===== AIRWISE DATA QUALITY AUDIT =====")
print("Total records:", total)
print("Duplicate groups:", duplicates)
print("Missing values:", missing_values)

print("\nPollutant distribution:")
for pollutant, count in pollutant_counts:
    print(pollutant, ":", count)

print("\nDate range:")
print("Earliest:", date_range[0])
print("Latest:", date_range[1])

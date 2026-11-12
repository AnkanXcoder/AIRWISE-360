
import pandas as pd
from sqlalchemy import text

from backend.database import get_connection


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

LOCATION_ID = 6950
SENSOR_ID = 12235887
POLLUTANT = "pm25"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_dataset():

    connection = get_connection()

    try:

        query = text("""
            SELECT
                sensor_id,
                pollutant,
                value,
                unit,
                observed_at
            FROM air_quality_measurements
            WHERE location_id = :location_id
            AND sensor_id = :sensor_id
            AND pollutant = :pollutant
            ORDER BY observed_at
        """)

        df = pd.read_sql_query(
            query,
            connection,
            params={
                "location_id": LOCATION_ID,
                "sensor_id": SENSOR_ID,
                "pollutant": POLLUTANT
            }
        )

    finally:
        connection.close()

    return df


# --------------------------------------------------
# PROFILE DATASET
# --------------------------------------------------

def profile_dataset():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - ML DATASET PROFILING")
    print("=" * 65)

    df = load_dataset()

    if df.empty:
        print("No records found.")
        return

    df["observed_at"] = pd.to_datetime(
        df["observed_at"],
        utc=True,
        errors="coerce"
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["observed_at", "value"]
    )

    df = df.sort_values("observed_at")

    print("\n[1] DATASET OVERVIEW")
    print("-" * 65)

    print("Rows:", len(df))
    print("Sensor:", SENSOR_ID)
    print("Pollutant:", POLLUTANT)
    print("Units:", df["unit"].unique().tolist())

    print("Start:", df["observed_at"].min())
    print("End:", df["observed_at"].max())

    print("\n[2] STATISTICAL SUMMARY")
    print("-" * 65)

    print(df["value"].describe())

    print("\n[3] TIME INTERVAL ANALYSIS")
    print("-" * 65)

    intervals = (
        df["observed_at"]
        .diff()
        .dt.total_seconds()
        .div(60)
        .dropna()
    )

    print("Median interval (minutes):", intervals.median())
    print("Mean interval (minutes):", intervals.mean())
    print("Maximum gap (minutes):", intervals.max())

    print(
        "Gaps > 60 minutes:",
        (intervals > 60).sum()
    )

    print("\n[4] MISSING INTERVAL ANALYSIS")
    print("-" * 65)

    expected_index = pd.date_range(
        start=df["observed_at"].min(),
        end=df["observed_at"].max(),
        freq="15min"
    )

    actual_index = pd.DatetimeIndex(
        df["observed_at"].drop_duplicates()
    )

    missing_timestamps = expected_index.difference(
        actual_index
    )

    print("Expected timestamps:", len(expected_index))
    print("Actual unique timestamps:", len(actual_index))
    print("Missing 15-minute timestamps:", len(missing_timestamps))

    print("\n[5] VALUE QUALITY")
    print("-" * 65)

    print("Missing values:", df["value"].isna().sum())
    print("Negative values:", (df["value"] < 0).sum())
    print("Infinite values:", (~df["value"].map(
        lambda x: pd.notna(x) and abs(x) != float("inf")
    )).sum())

    print("\n[6] DAILY OBSERVATIONS")
    print("-" * 65)

    daily = (
        df.set_index("observed_at")["value"]
        .resample("1D")
        .agg(["count", "mean", "min", "max"])
    )

    print(daily.to_string())

    print("\n[7] DUPLICATE TIMESTAMPS")
    print("-" * 65)

    print(
        "Duplicate timestamps:",
        df["observed_at"].duplicated().sum()
    )

    print("\n" + "=" * 65)
    print("PROFILING COMPLETED")
    print("=" * 65)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    profile_dataset()

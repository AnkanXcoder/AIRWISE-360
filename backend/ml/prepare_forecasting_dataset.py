
import pandas as pd
import numpy as np
from sqlalchemy import text

from backend.database import get_connection


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

LOCATION_ID = 6950
SENSOR_ID = 12235887
POLLUTANT = "pm25"

FREQUENCY = "15min"
FORECAST_STEPS = 4

TIMEZONE = "Asia/Kolkata"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_data():

    connection = get_connection()

    try:
        query = text("""
            SELECT
                observed_at,
                value,
                unit
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
# CREATE REGULAR TIME SERIES
# --------------------------------------------------

def create_regular_series(df):

    if df.empty:
        raise ValueError("No historical observations found.")

    df = df.copy()

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

    # Remove infinite values.
    df = df[np.isfinite(df["value"])]

    df = df.sort_values("observed_at")

    # Do not silently average duplicate timestamps.
    duplicate_count = df["observed_at"].duplicated().sum()

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate timestamps. "
            "Resolve them before feature generation."
        )

    df = df.set_index("observed_at")

    # Create a regular UTC 15-minute timeline.
    regular = df[["value"]].asfreq(FREQUENCY)

    # Convert timestamps to Kolkata time.
    regular.index = regular.index.tz_convert(TIMEZONE)

    return regular


# --------------------------------------------------
# BUILD FEATURES AND TARGET
# --------------------------------------------------

def build_forecasting_dataset(series):

    data = pd.DataFrame(index=series.index)

    values = series["value"]

    # 1. Current observation available at forecast time.
    data["pm25_current"] = values

    # 2. Historical lag features.
    data["pm25_lag_15m"] = values.shift(1)
    data["pm25_lag_30m"] = values.shift(2)
    data["pm25_lag_60m"] = values.shift(4)
    data["pm25_lag_120m"] = values.shift(8)

    # 3. Historical rolling statistics.
    # These use only current and past observations.

    data["pm25_rolling_mean_1h"] = (
        values.rolling(
            window=4,
            min_periods=4
        ).mean()
    )

    data["pm25_rolling_std_1h"] = (
        values.rolling(
            window=4,
            min_periods=4
        ).std()
    )

    # 4. Local calendar features.
    data["hour"] = data.index.hour

    data["day_of_week"] = data.index.day_of_week

    # 5. Cyclical time encoding.
    data["hour_sin"] = np.sin(
        2 * np.pi * data["hour"] / 24
    )

    data["hour_cos"] = np.cos(
        2 * np.pi * data["hour"] / 24
    )

    data["day_sin"] = np.sin(
        2 * np.pi * data["day_of_week"] / 7
    )

    data["day_cos"] = np.cos(
        2 * np.pi * data["day_of_week"] / 7
    )

    # 6. Forecasting target:
    # Average of the next four 15-minute observations.

    future_values = pd.concat(
        [
            values.shift(-step)
            for step in range(1, FORECAST_STEPS + 1)
        ],
        axis=1
    )

    future_values.columns = [
        f"future_{step}"
        for step in range(1, FORECAST_STEPS + 1)
    ]

    # Require all four future observations.
    data["target_pm25_next_hour"] = (
        future_values.mean(axis=1)
        .where(future_values.notna().all(axis=1))
    )

    # 7. Feature columns.
    # IMPORTANT: 13 features in total.

    feature_columns = [
        "pm25_current",
        "pm25_lag_15m",
        "pm25_lag_30m",
        "pm25_lag_60m",
        "pm25_lag_120m",
        "pm25_rolling_mean_1h",
        "pm25_rolling_std_1h",
        "hour",
        "day_of_week",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos"
    ]

    # Keep only rows with complete features and targets.
    dataset = data[
        feature_columns + ["target_pm25_next_hour"]
    ].dropna()

    return dataset, feature_columns


# --------------------------------------------------
# CHRONOLOGICAL SPLIT
# --------------------------------------------------

def chronological_split(dataset):

    total = len(dataset)

    train_end = int(total * 0.70)
    validation_end = int(total * 0.85)

    # Purge four rows between partitions.
    # This prevents overlapping one-hour target windows
    # across adjacent partitions.

    train = dataset.iloc[
        :max(0, train_end - FORECAST_STEPS)
    ]

    validation = dataset.iloc[
        train_end:max(
            train_end,
            validation_end - FORECAST_STEPS
        )
    ]

    test = dataset.iloc[validation_end:]

    return train, validation, test


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - FORECASTING DATASET PREPARATION")
    print("=" * 65)

    print("\n[1] Loading database observations...")

    df = load_data()

    print("Raw database records:", len(df))

    if df.empty:
        print("No data available.")
        return

    print("\n[2] Creating regular 15-minute time series...")

    series = create_regular_series(df)

    print("Expected timestamps:", len(series))

    print(
        "Available timestamps:",
        series["value"].notna().sum()
    )

    print(
        "Missing timestamps:",
        series["value"].isna().sum()
    )

    print("\n[3] Building forecasting features...")

    dataset, feature_columns = build_forecasting_dataset(series)

    print("Feature count:", len(feature_columns))

    print("Feature names:", feature_columns)

    print("Usable forecasting samples:", len(dataset))

    print("\n[4] Forecasting target statistics...")

    if not dataset.empty:
        print(dataset["target_pm25_next_hour"].describe())
    else:
        print("No usable targets.")
        return

    print("\n[5] Chronological dataset split...")

    train, validation, test = chronological_split(dataset)

    print("Training samples:", len(train))
    print("Validation samples:", len(validation))
    print("Testing samples:", len(test))

    print("\n[6] Time boundaries")

    print("First sample:", dataset.index.min())
    print("Last sample:", dataset.index.max())

    print("\nTraining period:")

    if not train.empty:
        print(train.index.min(), "to", train.index.max())

    print("\nValidation period:")

    if not validation.empty:
        print(
            validation.index.min(),
            "to",
            validation.index.max()
        )

    print("\nTesting period:")

    if not test.empty:
        print(test.index.min(), "to", test.index.max())

    print("\n" + "=" * 65)
    print("DATASET PREPARATION COMPLETED")
    print("Database unchanged. No model trained.")
    print("=" * 65)


if __name__ == "__main__":
    main()

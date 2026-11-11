
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)

from backend.ml.detect_pollution_surge import detect_surges


def main():

    print("\n" + "=" * 70)
    print("AIRWISE 360 - HISTORICAL SURGE DETECTOR PROFILE")
    print("=" * 70)

    df = load_data()
    series = create_regular_series(df)

    results = detect_surges(series)

    # Only actual detected observations.
    detected = results[results["surge_detected"]].copy()

    print("\n[1] Dataset overview")
    print("Total timeline rows:", len(results))
    print("Valid observations:", results["value"].notna().sum())
    print("Missing observations:", results["value"].isna().sum())

    print("\n[2] Detection overview")
    print("Detected observations:", len(detected))

    if detected.empty:
        print("No surge observations detected.")
        return

    print("\n[3] Detection dates")

    daily = detected.groupby(detected.index.date).agg(
        alerts=("value", "size"),
        maximum_pm25=("value", "max"),
        average_pm25=("value", "mean")
    )

    print(daily.round(2).to_string())

    print("\n[4] Largest detected observations")

    largest = detected.nlargest(
        10,
        "value"
    )[
        [
            "value",
            "baseline_median",
            "surge_threshold",
            "change_30m",
            "change_60m"
        ]
    ]

    print(largest.round(2).to_string())

    print("\n[5] Detection rate")

    valid_count = results["value"].notna().sum()

    detection_rate = (
        len(detected) / valid_count * 100
    )

    print(f"Detection rate: {detection_rate:.2f}%")

    print("\n[6] Missing observations around detections")

    for timestamp in detected.index:

        window_start = timestamp - pd.Timedelta(minutes=60)
        window_end = timestamp + pd.Timedelta(minutes=60)

        window = results.loc[window_start:window_end]

        missing_count = window["value"].isna().sum()

        print(
            timestamp,
            "| Missing observations in +/-60 min:",
            missing_count
        )

    print("\n" + "=" * 70)
    print("HISTORICAL SURGE PROFILE COMPLETED")
    print("No database changes.")
    print("=" * 70)


if __name__ == "__main__":
    main()

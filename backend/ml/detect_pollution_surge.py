
import numpy as np
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

WINDOW_SIZE = 4

MIN_ABSOLUTE_INCREASE = 15.0
MIN_RELATIVE_INCREASE = 1.4

MIN_30_MIN_INCREASE = 20.0
MIN_60_MIN_INCREASE = 30.0

MIN_VALID_BASELINE = 4


# --------------------------------------------------
# SURGE DETECTION
# --------------------------------------------------

def detect_surges(series):

    data = series.copy()

    values = data["value"]

    # Previous four observations only.
    previous_values = values.shift(1)

    rolling = previous_values.rolling(
        window=WINDOW_SIZE,
        min_periods=MIN_VALID_BASELINE
    )

    data["baseline_median"] = rolling.median()

    # Median Absolute Deviation.
    data["baseline_mad"] = rolling.apply(
        lambda x: np.median(
            np.abs(x - np.median(x))
        ),
        raw=True
    )

    # Robust dispersion estimate.
    data["robust_sigma"] = (
        1.4826 * data["baseline_mad"]
    )

    # Changes over 30 and 60 minutes.
    data["change_30m"] = values - values.shift(2)

    data["change_60m"] = values - values.shift(4)

    # Dynamic threshold with an absolute noise floor.
    data["surge_threshold"] = (
        data["baseline_median"]
        + np.maximum(
            3 * data["robust_sigma"],
            MIN_ABSOLUTE_INCREASE
        )
    )

    # Detection conditions.
    data["baseline_exceeded"] = (
        values > data["surge_threshold"]
    )

    data["relative_increase"] = (
        values >= (
            data["baseline_median"]
            * MIN_RELATIVE_INCREASE
        )
    )

    data["rapid_increase"] = (
        (data["change_30m"] >= MIN_30_MIN_INCREASE)
        |
        (data["change_60m"] >= MIN_60_MIN_INCREASE)
    )

    # Require all three signals.
    data["surge_detected"] = (
        data["baseline_median"].notna()
        & data["baseline_exceeded"]
        & data["relative_increase"]
        & data["rapid_increase"]
    )

    return data


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 75)
    print("AIRWISE 360 - POLLUTION SURGE DETECTOR")
    print("=" * 75)

    print("\n[1] Loading historical sensor observations...")

    df = load_data()

    series = create_regular_series(df)

    print("Available observations:", series["value"].notna().sum())

    print("\n[2] Running causal surge detection...")

    results = detect_surges(series)

    # Select the known event period.
    start = pd.Timestamp(
        "2026-11-08 18:00:00",
        tz="Asia/Kolkata"
    )

    end = pd.Timestamp(
        "2026-11-08 23:59:00",
        tz="Asia/Kolkata"
    )

    event = results.loc[start:end].copy()

    columns = [
        "value",
        "baseline_median",
        "surge_threshold",
        "change_30m",
        "change_60m",
        "surge_detected"
    ]

    print("\n[3] Event detection timeline")

    print(
        event[columns].round(2).to_string()
    )

    # 4. Detection summary.
    detected = event[event["surge_detected"]]

    print("\n[4] Detection summary")

    print("Event observations:", event["value"].notna().sum())

    print("Detected surge observations:", len(detected))

    if not detected.empty:

        print("First detection:", detected.index.min())

        print("Last detection:", detected.index.max())

        print(
            "Maximum detected PM2.5:",
            round(detected["value"].max(), 2)
        )

    else:

        print("No surge detected using current thresholds.")

    print("\n" + "=" * 75)
    print("SURGE DETECTION COMPLETED")
    print("No database changes. No model trained.")
    print("Thresholds are experimental, not official AQI limits.")
    print("=" * 75)


if __name__ == "__main__":
    main()

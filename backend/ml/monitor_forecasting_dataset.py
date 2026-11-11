
import numpy as np
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split
)


TARGET_COLUMN = "target_pm25_next_hour"

# Experimental trend classification threshold.
# This is NOT an official AQI threshold.
RAPID_CHANGE_THRESHOLD = 10.0

# Expected observation frequency.
INTERVAL_MINUTES = 15


def print_section(title):

    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)


# ==============================================================
# 1. HISTORICAL DATA QUALITY AND MISSING GAP SEVERITY
# ==============================================================

def monitor_data_quality(raw_df, series):

    print_section("1. HISTORICAL DATA QUALITY")

    observed_mask = series["value"].notna()

    observed = int(observed_mask.sum())
    expected = len(series)
    missing = expected - observed

    coverage = (
        observed / expected * 100
        if expected > 0
        else 0
    )

    print("Raw database records:", len(raw_df))
    print("Expected 15-minute intervals:", expected)
    print("Observed intervals:", observed)
    print("Missing intervals:", missing)
    print("Temporal coverage:", round(coverage, 2), "%")

    print("First observation:", series.index.min())
    print("Last observation:", series.index.max())

    print(
        "Observation days:",
        series.loc[observed_mask].index.normalize().nunique()
    )

    # Identify consecutive groups of missing intervals.
    missing_mask = ~observed_mask

    group_ids = missing_mask.ne(
        missing_mask.shift(fill_value=False)
    ).cumsum()

    missing_groups = (
        series.loc[missing_mask]
        .groupby(group_ids[missing_mask])
        .size()
    )

    # Convert missing interval counts into minutes.
    gap_durations = missing_groups * INTERVAL_MINUTES

    print("\n[MISSING GAP SEVERITY]")

    print("Number of separate gaps:", len(gap_durations))

    if not gap_durations.empty:

        print(
            "Longest gap (hours):",
            round(gap_durations.max() / 60, 2)
        )

        print(
            "Gaps longer than 1 hour:",
            int((gap_durations > 60).sum())
        )

        print(
            "Gaps longer than 6 hours:",
            int((gap_durations > 360).sum())
        )

        print(
            "Gaps longer than 24 hours:",
            int((gap_durations > 1440).sum())
        )

        print(
            "Average gap duration (minutes):",
            round(gap_durations.mean(), 2)
        )

    else:

        print("No missing gaps detected.")

    if missing > 0:

        print("\nData quality warning: Missing intervals detected.")

    else:

        print("\nData quality: No missing intervals detected.")

    return {
        "observed": observed,
        "expected": expected,
        "missing": missing,
        "coverage": coverage,
        "gap_count": len(gap_durations),
        "longest_gap_minutes": (
            int(gap_durations.max())
            if not gap_durations.empty
            else 0
        )
    }


# ==============================================================
# 2. PM2.5 CONCENTRATION DISTRIBUTION
# ==============================================================

def monitor_concentration_distribution(series):

    print_section("2. PM2.5 CONCENTRATION DISTRIBUTION")

    values = series["value"].dropna()

    if values.empty:

        print("No valid PM2.5 observations available.")
        return

    statistics = values.describe(
        percentiles=[0.25, 0.50, 0.75, 0.90, 0.95]
    )

    print(statistics.round(3).to_string())

    print("\nAdditional checks:")

    print("Negative values:", int((values < 0).sum()))

    print("Zero values:", int((values == 0).sum()))

    print(
        "Non-finite values:",
        int((~np.isfinite(values)).sum())
    )


# ==============================================================
# 3. CHRONOLOGICAL SPLIT MONITORING
# ==============================================================

def monitor_forecasting_splits(
    train,
    validation,
    test,
    feature_columns
):

    print_section("3. CHRONOLOGICAL SPLIT MONITORING")

    splits = [
        ("Training", train),
        ("Validation", validation),
        ("Test", test)
    ]

    for name, data in splits:

        print(f"\n{name}")

        print("Samples:", len(data))

        if data.empty:

            print("Warning: Empty split.")
            continue

        print("Start:", data.index.min())

        print("End:", data.index.max())

        print(
            "Missing feature values:",
            int(data[feature_columns].isna().sum().sum())
        )

        print(
            "Missing target values:",
            int(data[TARGET_COLUMN].isna().sum())
        )

        print(
            "Duplicate timestamps:",
            int(data.index.duplicated().sum())
        )

    # Verify chronological ordering between partitions.
    chronological = (
        train.index.max() < validation.index.min()
        and validation.index.max() < test.index.min()
    )

    print("\nChronological ordering:", chronological)

    return chronological


# ==============================================================
# 4. POLLUTION TREND EVENT MONITORING
# ==============================================================

def monitor_pollution_trends(
    train,
    validation,
    test
):

    print_section("4. POLLUTION TREND EVENT MONITORING")

    splits = [
        ("Training", train),
        ("Validation", validation),
        ("Test", test)
    ]

    for name, data in splits:

        if data.empty:
            continue

        change_30m = (
            data["pm25_current"]
            - data["pm25_lag_30m"]
        )

        rising = change_30m >= RAPID_CHANGE_THRESHOLD

        falling = change_30m <= -RAPID_CHANGE_THRESHOLD

        stable = (
            (change_30m > -RAPID_CHANGE_THRESHOLD)
            & (change_30m < RAPID_CHANGE_THRESHOLD)
        )

        print(f"\n{name}")

        print("Total samples:", len(data))

        print("Rapidly rising:", int(rising.sum()))

        print("Rapidly falling:", int(falling.sum()))

        print("Relatively stable:", int(stable.sum()))

        print(
            "Maximum 30-minute increase:",
            round(change_30m.max(), 3)
        )

        print(
            "Minimum 30-minute change:",
            round(change_30m.min(), 3)
        )


# ==============================================================
# 5. FORECASTING FEATURE MONITORING
# ==============================================================

def monitor_feature_distribution(
    train,
    validation,
    test,
    feature_columns
):

    print_section("5. FORECASTING FEATURE MONITORING")

    print("Total forecasting features:", len(feature_columns))

    print("\nFeature names:")

    for feature in feature_columns:

        print("-", feature)

    splits = [
        ("Training", train),
        ("Validation", validation),
        ("Test", test)
    ]

    for name, data in splits:

        if data.empty:
            continue

        print(f"\n{name} feature availability")

        missing_features = int(
            data[feature_columns].isna().sum().sum()
        )

        print("Missing feature values:", missing_features)

        print(
            "Feature completeness:",
            "Complete" if missing_features == 0 else "Incomplete"
        )


# ==============================================================
# 6. DATASET MONITORING SUMMARY
# ==============================================================

def print_monitoring_summary(
    raw_df,
    dataset,
    train,
    validation,
    test,
    feature_columns,
    quality,
    chronological
):

    print_section("6. DATASET MONITORING SUMMARY")

    print("Raw observations:", len(raw_df))

    print("Forecasting samples:", len(dataset))

    print("Training samples:", len(train))

    print("Validation samples:", len(validation))

    print("Test samples:", len(test))

    print("Feature count:", len(feature_columns))

    print(
        "Temporal coverage:",
        round(quality["coverage"], 2),
        "%"
    )

    print("Missing intervals:", quality["missing"])

    print("Separate missing gaps:", quality["gap_count"])

    print(
        "Longest gap (minutes):",
        quality["longest_gap_minutes"]
    )

    print("Chronological ordering:", chronological)

    if quality["missing"] > 0 or not chronological:

        status = "REVIEW REQUIRED"

    else:

        status = "INITIAL CHECKS PASSED"

    print("\nMonitoring status:", status)

    print("\nNo model trained.")

    print("No database records modified.")


# ==============================================================
# 7. MAIN EXECUTION
# ==============================================================

def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - FORECASTING DATASET MONITOR")
    print("=" * 65)

    # 1. Load historical observations.
    raw_df = load_data()

    if raw_df.empty:

        raise ValueError("No historical observations found.")

    # 2. Create regular 15-minute time series.
    series = create_regular_series(raw_df)

    if series.empty:

        raise ValueError(
            "Unable to create a regular time series."
        )

    # 3. Build forecasting dataset.
    dataset, feature_columns = build_forecasting_dataset(series)

    if dataset.empty:

        raise ValueError("Forecasting dataset is empty.")

    # 4. Create chronological splits.
    train, validation, test = chronological_split(dataset)

    if train.empty or validation.empty or test.empty:

        raise ValueError(
            "One or more chronological splits are empty."
        )

    # 5. Run data quality monitoring.
    quality = monitor_data_quality(raw_df, series)

    # 6. Analyze PM2.5 concentration distribution.
    monitor_concentration_distribution(series)

    # 7. Check chronological partitions.
    chronological = monitor_forecasting_splits(
        train,
        validation,
        test,
        feature_columns
    )

    # 8. Analyze pollution trends.
    monitor_pollution_trends(
        train,
        validation,
        test
    )

    # 9. Check forecasting feature completeness.
    monitor_feature_distribution(
        train,
        validation,
        test,
        feature_columns
    )

    # 10. Print final monitoring summary.
    print_monitoring_summary(
        raw_df,
        dataset,
        train,
        validation,
        test,
        feature_columns,
        quality,
        chronological
    )

    print("\n" + "=" * 65)
    print("FORECASTING DATASET MONITORING COMPLETED")
    print("=" * 65)


if __name__ == "__main__":

    main()


import numpy as np
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split
)


TARGET_COLUMN = "target_pm25_next_hour"


def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - TEMPORAL FORECAST ERROR ANALYSIS")
    print("=" * 65)

    # ==========================================================
    # 1. LOAD DATA AND PREPARE CHRONOLOGICAL SPLITS
    # ==========================================================

    df = load_data()

    series = create_regular_series(df)

    dataset, feature_columns = build_forecasting_dataset(series)

    train, validation, test = chronological_split(dataset)

    if train.empty or validation.empty or test.empty:
        raise ValueError("One or more chronological splits are empty.")

    # ==========================================================
    # 2. DIAGNOSE POLLUTION TREND DISTRIBUTION
    # ==========================================================

    print("\n[SPLIT DIAGNOSTICS] Pollution trend distribution")

    splits = [
        ("Training", train),
        ("Validation", validation),
        ("Test", test)
    ]

    for split_name, split_data in splits:

        change_30m = (
            split_data["pm25_current"]
            - split_data["pm25_lag_30m"]
        )

        print(f"\n{split_name}")
        print("Total samples:", len(split_data))
        print("Rapidly rising:", (change_30m >= 10).sum())
        print("Rapidly falling:", (change_30m <= -10).sum())

        print(
            "Relatively stable:",
            ((change_30m > -10) & (change_30m < 10)).sum()
        )

        print(
            "Maximum 30-minute increase:",
            round(change_30m.max(), 3)
        )

        print(
            "Minimum 30-minute change:",
            round(change_30m.min(), 3)
        )

    # ==========================================================
    # 3. VALIDATION-ONLY TREND-BASED PERSISTENCE ANALYSIS
    # ==========================================================

    print("\n[VALIDATION] Trend-based persistence analysis")

    validation_results = validation[
        [
            TARGET_COLUMN,
            "pm25_current",
            "pm25_lag_30m"
        ]
    ].copy()

    # Persistence prediction: next-hour average is predicted
    # using the latest available PM2.5 observation.
    validation_results["prediction"] = (
        validation_results["pm25_current"]
    )

    validation_results["absolute_error"] = (
        validation_results[TARGET_COLUMN]
        - validation_results["prediction"]
    ).abs()

    validation_results["squared_error"] = (
        validation_results["absolute_error"] ** 2
    )

    validation_results["change_30m"] = (
        validation_results["pm25_current"]
        - validation_results["pm25_lag_30m"]
    )

    validation_results["trend"] = np.select(
        [
            validation_results["change_30m"] >= 10,
            validation_results["change_30m"] <= -10
        ],
        [
            "Rapidly Rising",
            "Rapidly Falling"
        ],
        default="Relatively Stable"
    )

    validation_summary = validation_results.groupby(
        "trend"
    ).agg(
        samples=("absolute_error", "size"),
        MAE=("absolute_error", "mean"),
        RMSE=(
            "squared_error",
            lambda x: np.sqrt(x.mean())
        )
    )

    print(validation_summary.round(3).to_string())

    # ==========================================================
    # 4. TEST-SET PERSISTENCE PREDICTIONS
    # ==========================================================

    print("\n[TEST] Preparing persistence predictions")

    results = test[
        [
            TARGET_COLUMN,
            "pm25_current",
            "pm25_lag_30m"
        ]
    ].copy()

    results["prediction"] = results["pm25_current"]

    results["error"] = (
        results[TARGET_COLUMN]
        - results["prediction"]
    )

    results["absolute_error"] = results["error"].abs()

    results["squared_error"] = results["error"] ** 2

    # ==========================================================
    # 5. POLLUTION CONCENTRATION REGIME ANALYSIS
    # ==========================================================

    print("\n[2] Pollution concentration regime analysis")

    # Calculate concentration thresholds using training data only.
    quantile_thresholds = train["pm25_current"].quantile(
        [0.25, 0.50, 0.75]
    ).to_numpy()

    # Create unique boundaries to handle tied quantiles safely.
    boundaries = np.unique(
        np.concatenate(
            ([-np.inf], quantile_thresholds, [np.inf])
        )
    )

    regime_labels = [
        f"Regime {i + 1}"
        for i in range(len(boundaries) - 1)
    ]

    results["pollution_regime"] = pd.cut(
        results["pm25_current"],
        bins=boundaries,
        labels=regime_labels,
        include_lowest=True
    )

    regime_analysis = results.groupby(
        "pollution_regime",
        observed=False
    ).agg(
        samples=("absolute_error", "size"),
        mean_current_pm25=("pm25_current", "mean"),
        mean_actual_target=(TARGET_COLUMN, "mean"),
        MAE=("absolute_error", "mean"),
        RMSE=(
            "squared_error",
            lambda x: np.sqrt(x.mean())
        )
    )

    print("Training-derived thresholds:")
    print(np.round(quantile_thresholds, 3))

    print("\nRegime-wise forecasting performance:")
    print(regime_analysis.round(3).to_string())

    # ==========================================================
    # 6. POLLUTION TREND AND FORECASTING ERROR ANALYSIS
    # ==========================================================

    print("\n[3] Pollution trend analysis")

    # Calculate concentration change over the previous 30 minutes.
    results["change_30m"] = (
        results["pm25_current"]
        - results["pm25_lag_30m"]
    )

    # Experimental trend thresholds: +/- 10 micrograms/m3
    # over 30 minutes. These are not official AQI thresholds.
    results["pollution_trend"] = np.select(
        [
            results["change_30m"] >= 10,
            results["change_30m"] <= -10
        ],
        [
            "Rapidly Rising",
            "Rapidly Falling"
        ],
        default="Relatively Stable"
    )

    trend_analysis = results.groupby(
        "pollution_trend",
        observed=False
    ).agg(
        samples=("absolute_error", "size"),
        mean_change_30m=("change_30m", "mean"),
        MAE=("absolute_error", "mean"),
        RMSE=(
            "squared_error",
            lambda x: np.sqrt(x.mean())
        )
    )

    print(trend_analysis.round(3).to_string())

    # ==========================================================
    # 7. OVERALL PERSISTENCE TEST PERFORMANCE
    # ==========================================================

    print("\n[1] Overall persistence test performance")

    print("Samples:", len(results))

    print(
        "MAE:",
        round(results["absolute_error"].mean(), 4)
    )

    print(
        "RMSE:",
        round(np.sqrt(results["squared_error"].mean()), 4)
    )

    # ==========================================================
    # 8. DAILY ERROR ANALYSIS
    # ==========================================================

    print("\n[4] Daily error analysis")

    results["date"] = results.index.date

    daily = results.groupby("date").agg(
        samples=("absolute_error", "size"),
        MAE=("absolute_error", "mean"),
        RMSE=(
            "squared_error",
            lambda x: np.sqrt(x.mean())
        ),
        mean_actual=(TARGET_COLUMN, "mean"),
        max_actual=(TARGET_COLUMN, "max")
    )

    print(daily.round(3).to_string())

    # ==========================================================
    # 9. HOURLY ERROR ANALYSIS
    # ==========================================================

    print("\n[5] Hourly error analysis")

    results["hour"] = results.index.hour

    hourly = results.groupby("hour").agg(
        samples=("absolute_error", "size"),
        MAE=("absolute_error", "mean"),
        RMSE=(
            "squared_error",
            lambda x: np.sqrt(x.mean())
        )
    )

    print(hourly.round(3).to_string())

    # ==========================================================
    # 10. LARGEST PREDICTION ERRORS
    # ==========================================================

    print("\n[6] Top 10 largest prediction errors")

    largest_errors = results.nlargest(
        10,
        "absolute_error"
    )[
        [
            TARGET_COLUMN,
            "prediction",
            "error",
            "absolute_error"
        ]
    ]

    print(largest_errors.round(3).to_string())

    # ==========================================================
    # 11. ERROR DIRECTION ANALYSIS
    # ==========================================================

    print("\n[7] Error direction")

    print(
        "Underprediction count:",
        (results["error"] > 0).sum()
    )

    print(
        "Overprediction count:",
        (results["error"] < 0).sum()
    )

    print(
        "Exact prediction count:",
        (results["error"] == 0).sum()
    )

    # ==========================================================
    # 12. COMPLETION
    # ==========================================================

    print("\n" + "=" * 65)
    print("TEMPORAL ERROR ANALYSIS COMPLETED")
    print("No model trained. Database unchanged.")
    print("=" * 65)


if __name__ == "__main__":
    main()

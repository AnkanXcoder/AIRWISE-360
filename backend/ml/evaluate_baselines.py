
import numpy as np
import pandas as pd

from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEASONAL_LAG = pd.Timedelta(days=1)

TARGET_COLUMN = "target_pm25_next_hour"


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def calculate_metrics(actual, predicted):

    mae = mean_absolute_error(actual, predicted)

    rmse = np.sqrt(
        mean_squared_error(actual, predicted)
    )

    return mae, rmse


def evaluate_baseline(name, actual, predicted):

    valid = (
        actual.notna()
        & predicted.notna()
        & np.isfinite(actual)
        & np.isfinite(predicted)
    )

    actual_valid = actual.loc[valid]
    predicted_valid = predicted.loc[valid]

    if len(actual_valid) == 0:
        print(f"\n{name}: No valid predictions.")
        return

    mae, rmse = calculate_metrics(
        actual_valid,
        predicted_valid
    )

    print(f"\n{name}")
    print("-" * 50)
    print("Evaluated samples:", len(actual_valid))
    print(f"MAE:  {mae:.4f} µg/m³")
    print(f"RMSE: {rmse:.4f} µg/m³")


# --------------------------------------------------
# BASELINE PREDICTIONS
# --------------------------------------------------

def build_baseline_predictions(series, dataset):

    # Persistence:
    # Use the latest available observation at forecast time.
    persistence = series["value"].reindex(
        dataset.index
    )

    # Seasonal naive:
    # Use the previous day's corresponding next-hour target.
    previous_day_index = (
        dataset.index - SEASONAL_LAG
    )

    seasonal = pd.Series(
        dataset[TARGET_COLUMN].reindex(
            previous_day_index
        ).to_numpy(),
        index=dataset.index,
        name="seasonal_prediction"
    )

    return persistence, seasonal


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - BASELINE MODEL EVALUATION")
    print("=" * 65)

    # Load original observations.
    print("\n[1] Loading observations...")

    df = load_data()

    if df.empty:
        raise ValueError("No observations found.")

    print("Raw records:", len(df))

    # Build regular time series.
    print("\n[2] Preparing time series...")

    series = create_regular_series(df)

    # Create forecasting dataset.
    print("\n[3] Creating forecasting samples...")

    dataset, feature_columns = (
        build_forecasting_dataset(series)
    )

    print("Features:", len(feature_columns))
    print("Usable samples:", len(dataset))

    # Chronological split.
    print("\n[4] Creating chronological splits...")

    train, validation, test = chronological_split(
        dataset
    )

    print("Training samples:", len(train))
    print("Validation samples:", len(validation))
    print("Testing samples:", len(test))

    # Generate baseline predictions.
    print("\n[5] Generating baseline predictions...")

    persistence, seasonal = (
        build_baseline_predictions(
            series,
            dataset
        )
    )

    actual = dataset[TARGET_COLUMN]

    # Validation evaluation.
    print("\n" + "=" * 65)
    print("VALIDATION RESULTS")
    print("=" * 65)

    evaluate_baseline(
        "Persistence Baseline",
        actual.loc[validation.index],
        persistence.loc[validation.index]
    )

    evaluate_baseline(
        "Seasonal Naive Baseline (24 hours)",
        actual.loc[validation.index],
        seasonal.loc[validation.index]
    )

    # Test evaluation.
    print("\n" + "=" * 65)
    print("TEST RESULTS")
    print("=" * 65)

    evaluate_baseline(
        "Persistence Baseline",
        actual.loc[test.index],
        persistence.loc[test.index]
    )

    evaluate_baseline(
        "Seasonal Naive Baseline (24 hours)",
        actual.loc[test.index],
        seasonal.loc[test.index]
    )

    print("\n" + "=" * 65)
    print("BASELINE EVALUATION COMPLETED")
    print("No model trained. Database unchanged.")
    print("=" * 65)


if __name__ == "__main__":
    main()


import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

RANDOM_STATE = 42

TARGET_COLUMN = "target_pm25_next_hour"

MODEL_PARAMETERS = {
    "n_estimators": 300,
    "max_depth": 12,
    "min_samples_split": 10,
    "min_samples_leaf": 4,
    "max_features": 0.8,
    "random_state": RANDOM_STATE,
    "n_jobs": -1
}


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def calculate_metrics(y_true, y_pred):

    mae = mean_absolute_error(y_true, y_pred)

    rmse = np.sqrt(
        mean_squared_error(y_true, y_pred)
    )

    r2 = r2_score(y_true, y_pred)

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - RANDOM FOREST MODEL TRAINING")
    print("=" * 65)

    # 1. Load and prepare dataset.

    print("\n[1] Loading historical observations...")

    df = load_data()

    print("Raw observations:", len(df))

    series = create_regular_series(df)

    dataset, feature_columns = build_forecasting_dataset(series)

    train, validation, test = chronological_split(dataset)

    if train.empty or validation.empty or test.empty:
        raise ValueError("Training, validation, or test dataset is empty.")

    print("Features:", len(feature_columns))
    print("Training samples:", len(train))
    print("Validation samples:", len(validation))
    print("Testing samples:", len(test))

    # 2. Prepare X and y.

    X_train = train[feature_columns]
    y_train = train[TARGET_COLUMN]

    X_validation = validation[feature_columns]
    y_validation = validation[TARGET_COLUMN]

    X_test = test[feature_columns]
    y_test = test[TARGET_COLUMN]

    # 3. Train Random Forest.

    print("\n[2] Training Random Forest...")

    model = RandomForestRegressor(
        **MODEL_PARAMETERS
    )

    model.fit(X_train, y_train)

    print("Model training completed.")

    # 4. Validation evaluation.

    print("\n[3] Validation evaluation...")

    validation_predictions = model.predict(X_validation)

    validation_metrics = calculate_metrics(
        y_validation,
        validation_predictions
    )

    for metric, value in validation_metrics.items():
        print(f"{metric}: {value:.4f}")

    # 5. Test evaluation.

    print("\n[4] Test evaluation...")

    test_predictions = model.predict(X_test)

    test_metrics = calculate_metrics(
        y_test,
        test_predictions
    )

    for metric, value in test_metrics.items():
        print(f"{metric}: {value:.4f}")

    # 6. Persistence baseline on identical test timestamps.
    # Current PM2.5 is the persistence prediction.

    print("\n[5] Persistence baseline comparison...")

    persistence_predictions = X_test["pm25_current"].to_numpy()

    persistence_metrics = calculate_metrics(
        y_test,
        persistence_predictions
    )

    print("\nMODEL COMPARISON")
    print("-" * 65)

    print(
        f"{'Metric':<12}"
        f"{'Random Forest':>18}"
        f"{'Persistence':>18}"
    )

    print("-" * 65)

    for metric in ["MAE", "RMSE", "R2"]:

        print(
            f"{metric:<12}"
            f"{test_metrics[metric]:>18.4f}"
            f"{persistence_metrics[metric]:>18.4f}"
        )

    # 7. Feature importance.

    print("\n[6] Feature importance...")

    importance = pd.DataFrame({
        "feature": feature_columns,
        "importance": model.feature_importances_
    })

    importance = importance.sort_values(
        by="importance",
        ascending=False
    )

    print(importance.to_string(index=False))

    # 8. Final result.

    print("\n[7] Model assessment...")

    if test_metrics["MAE"] < persistence_metrics["MAE"]:

        print(
            "Random Forest achieved lower test MAE "
            "than the persistence baseline."
        )

    else:

        print(
            "Random Forest did not beat the persistence "
            "baseline on test MAE."
        )

    print("\n" + "=" * 65)
    print("MODEL EVALUATION COMPLETED")
    print("No model file saved. Database unchanged.")
    print("=" * 65)


if __name__ == "__main__":
    main()

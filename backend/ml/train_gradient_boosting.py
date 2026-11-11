
import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split
)


TARGET_COLUMN = "target_pm25_next_hour"


def evaluate(y_true, predictions):

    return {
        "MAE": mean_absolute_error(y_true, predictions),
        "RMSE": np.sqrt(mean_squared_error(y_true, predictions)),
        "R2": r2_score(y_true, predictions)
    }


def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - HISTOGRAM GRADIENT BOOSTING")
    print("=" * 65)

    # 1. Load dataset.
    df = load_data()

    series = create_regular_series(df)

    dataset, feature_columns = build_forecasting_dataset(series)

    train, validation, test = chronological_split(dataset)

    print("\nDataset information")
    print("Features:", len(feature_columns))
    print("Training:", len(train))
    print("Validation:", len(validation))

    # 2. Prepare data.
    X_train = train[feature_columns]
    y_train = train[TARGET_COLUMN]

    X_validation = validation[feature_columns]
    y_validation = validation[TARGET_COLUMN]

    # 3. Build model.
    model = HistGradientBoostingRegressor(
        max_iter=200,
        learning_rate=0.05,
        max_leaf_nodes=15,
        l2_regularization=5.0,
        min_samples_leaf=20,
        random_state=42
    )

    # 4. Train.
    print("\nTraining Gradient Boosting...")

    model.fit(X_train, y_train)

    print("Training completed.")

    # 5. Predict.
    predictions = model.predict(X_validation)

    # 6. Evaluate.
    model_metrics = evaluate(
        y_validation,
        predictions
    )

    # 7. Persistence baseline.
    persistence_predictions = (
        X_validation["pm25_current"].to_numpy()
    )

    persistence_metrics = evaluate(
        y_validation,
        persistence_predictions
    )

    # 8. Compare.
    print("\nVALIDATION COMPARISON")
    print("-" * 65)

    print(
        f"{'Metric':<12}"
        f"{'Gradient Boosting':>20}"
        f"{'Persistence':>18}"
    )

    print("-" * 65)

    for metric in ["MAE", "RMSE", "R2"]:

        print(
            f"{metric:<12}"
            f"{model_metrics[metric]:>20.4f}"
            f"{persistence_metrics[metric]:>18.4f}"
        )

    # 9. Assessment.
    print("\nASSESSMENT")

    if model_metrics["MAE"] < persistence_metrics["MAE"]:
        print("Gradient Boosting beat persistence on validation MAE.")
    else:
        print("Gradient Boosting did not beat persistence.")

    print("\n" + "=" * 65)
    print("GRADIENT BOOSTING EXPERIMENT COMPLETED")
    print("Validation only. No model saved.")
    print("Database unchanged.")
    print("=" * 65)


if __name__ == "__main__":
    main()

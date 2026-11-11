
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
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
ALPHA = 10.0


def evaluate_model(y_true, predictions):

    return {
        "MAE": mean_absolute_error(y_true, predictions),
        "RMSE": np.sqrt(
            mean_squared_error(y_true, predictions)
        ),
        "R2": r2_score(y_true, predictions)
    }


def main():

    print("\n" + "=" * 65)
    print("AIRWISE 360 - RIDGE REGRESSION EXPERIMENT")
    print("=" * 65)

    # 1. Load dataset
    print("\n[1] Loading dataset...")

    df = load_data()
    series = create_regular_series(df)

    dataset, feature_columns = build_forecasting_dataset(series)

    train, validation, test = chronological_split(dataset)

    if train.empty or validation.empty:
        raise ValueError("Training or validation dataset is empty.")

    print("Features:", len(feature_columns))
    print("Training samples:", len(train))
    print("Validation samples:", len(validation))

    # 2. Prepare features and target
    X_train = train[feature_columns]
    y_train = train[TARGET_COLUMN]

    X_validation = validation[feature_columns]
    y_validation = validation[TARGET_COLUMN]

    # 3. Build Ridge pipeline
    print("\n[2] Building Ridge Regression pipeline...")

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=ALPHA))
    ])

    # 4. Train
    print("\n[3] Training model...")

    model.fit(X_train, y_train)

    print("Training completed.")

    # 5. Validation predictions
    print("\n[4] Evaluating validation data...")

    ridge_predictions = model.predict(X_validation)

    ridge_metrics = evaluate_model(
        y_validation,
        ridge_predictions
    )

    # 6. Persistence baseline
    persistence_predictions = (
        X_validation["pm25_current"].to_numpy()
    )

    persistence_metrics = evaluate_model(
        y_validation,
        persistence_predictions
    )

    # 7. Compare
    print("\n[5] Validation comparison")
    print("-" * 65)

    print(
        f"{'Metric':<12}"
        f"{'Ridge':>18}"
        f"{'Persistence':>18}"
    )

    print("-" * 65)

    for metric in ["MAE", "RMSE", "R2"]:

        print(
            f"{metric:<12}"
            f"{ridge_metrics[metric]:>18.4f}"
            f"{persistence_metrics[metric]:>18.4f}"
        )

    # 8. Coefficients
    print("\n[6] Ridge coefficients")

    coefficients = pd.DataFrame({
        "feature": feature_columns,
        "coefficient": model.named_steps["ridge"].coef_
    })

    coefficients["absolute_coefficient"] = (
        coefficients["coefficient"].abs()
    )

    coefficients = coefficients.sort_values(
        "absolute_coefficient",
        ascending=False
    )

    print(
        coefficients[
            ["feature", "coefficient"]
        ].to_string(index=False)
    )

    # 9. Assessment
    print("\n[7] Assessment")

    if ridge_metrics["MAE"] < persistence_metrics["MAE"]:
        print("Ridge outperformed persistence on validation MAE.")
    else:
        print("Ridge did not outperform persistence on validation MAE.")

    print("\n" + "=" * 65)
    print("RIDGE EXPERIMENT COMPLETED")
    print("Validation only. No model saved.")
    print("Database unchanged.")
    print("=" * 65)


if __name__ == "__main__":
    main()

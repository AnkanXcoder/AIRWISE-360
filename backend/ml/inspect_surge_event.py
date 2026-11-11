
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)


def main():

    print("\n" + "=" * 75)
    print("AIRWISE 360 - POLLUTION SURGE EVENT INVESTIGATION")
    print("=" * 75)

    # 1. Load observations.
    df = load_data()

    series = create_regular_series(df)

    # 2. Select the suspected event window.
    start = pd.Timestamp("2026-11-08 18:00:00", tz="Asia/Kolkata")
    end = pd.Timestamp("2026-11-08 23:59:00", tz="Asia/Kolkata")

    event = series.loc[start:end].copy()

    if event.empty:
        print("No observations found in the selected period.")
        return

    # 3. Create diagnostic columns.
    event["previous_pm25"] = series["value"].shift(1).reindex(event.index)

    event["change_from_previous"] = (
        event["value"] - event["previous_pm25"]
    )

    event["percentage_change"] = (
        event["change_from_previous"]
        / event["previous_pm25"].replace(0, float("nan"))
    ) * 100

    # 4. Calculate next-hour observations.
    for step in range(1, 5):
        event[f"future_{step * 15}m"] = (
            series["value"].shift(-step).reindex(event.index)
        )

    future_columns = [
        f"future_{step * 15}m"
        for step in range(1, 5)
    ]

    event["next_hour_mean"] = (
        event[future_columns]
        .mean(axis=1)
        .where(event[future_columns].notna().all(axis=1))
    )

    event["persistence_error"] = (
        event["next_hour_mean"] - event["value"]
    )

    # 5. Print detailed timeline.
    print("\n[1] Sensor observation timeline")
    print("All concentrations are in µg/m³.")
    print("NaN means no observation was available.")

    columns = [
        "value",
        "change_from_previous",
        "percentage_change",
        "future_15m",
        "future_30m",
        "future_45m",
        "future_60m",
        "next_hour_mean",
        "persistence_error"
    ]

    print(event[columns].round(2).to_string())

    # 6. Check largest observed concentration.
    print("\n[2] Event statistics")

    print("Available observations:", event["value"].count())
    print("Missing timestamps:", event["value"].isna().sum())
    print("Minimum:", event["value"].min())
    print("Maximum:", event["value"].max())
    print("Mean:", event["value"].mean())
    print("Median:", event["value"].median())

    # 7. Identify large positive changes.
    print("\n[3] Largest positive observation changes")

    increases = event.nlargest(
        5,
        "change_from_previous"
    )[
        [
            "previous_pm25",
            "value",
            "change_from_previous",
            "percentage_change"
        ]
    ]

    print(increases.round(2).to_string())

    print("\n" + "=" * 75)
    print("EVENT INVESTIGATION COMPLETED")
    print("No data modified. No model trained.")
    print("=" * 75)


if __name__ == "__main__":
    main()


import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)


def inspect_window(series, start, end, label):

    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    window = series.loc[start:end].copy()

    window["change_15m"] = window["value"].diff()

    window["change_30m"] = (
        window["value"] - window["value"].shift(2)
    )

    print(window.round(2).to_string())

    print("\nValid observations:", window["value"].notna().sum())
    print("Missing observations:", window["value"].isna().sum())

    print("Minimum:", window["value"].min())
    print("Maximum:", window["value"].max())


def main():

    df = load_data()

    series = create_regular_series(df)

    inspect_window(
        series,
        pd.Timestamp("2026-11-08 22:00", tz="Asia/Kolkata"),
        pd.Timestamp("2026-11-09 03:00", tz="Asia/Kolkata"),
        "NOVEMBER 8 SURGE: RECOVERY INVESTIGATION"
    )

    inspect_window(
        series,
        pd.Timestamp("2026-11-09 20:00", tz="Asia/Kolkata"),
        pd.Timestamp("2026-11-10 03:00", tz="Asia/Kolkata"),
        "NOVEMBER 9 INCREASE: RECOVERY INVESTIGATION"
    )

    print("\nRecovery investigation completed.")
    print("No database changes.")


if __name__ == "__main__":
    main()


import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)

from backend.ml.detect_pollution_surge import detect_surges


def main():

    print("\n" + "=" * 75)
    print("AIRWISE 360 - ALL SURGE EVENT INVESTIGATION")
    print("=" * 75)

    df = load_data()
    series = create_regular_series(df)

    results = detect_surges(series)

    detected = results[results["surge_detected"]]

    if detected.empty:
        print("No surge observations detected.")
        return

    # Group consecutive detected observations into episodes.
    # A gap greater than 30 minutes starts a new episode.

    episodes = []
    current_episode = []

    for timestamp in detected.index:

        if not current_episode:
            current_episode = [timestamp]
            continue

        previous = current_episode[-1]

        if timestamp - previous <= pd.Timedelta(minutes=30):
            current_episode.append(timestamp)
        else:
            episodes.append(current_episode)
            current_episode = [timestamp]

    if current_episode:
        episodes.append(current_episode)

    print("\n[1] Detected episodes")

    for number, episode in enumerate(episodes, start=1):

        print(
            f"Episode {number}: "
            f"{episode[0]} to {episode[-1]} "
            f"({len(episode)} triggered observations)"
        )

    print("\n[2] Surrounding observation timelines")

    for number, episode in enumerate(episodes, start=1):

        first = episode[0]
        last = episode[-1]

        start = first - pd.Timedelta(minutes=60)
        end = last + pd.Timedelta(minutes=60)

        window = results.loc[start:end].copy()

        print("\n" + "-" * 75)
        print(f"EPISODE {number}")
        print("-" * 75)

        columns = [
            "value",
            "baseline_median",
            "surge_threshold",
            "change_30m",
            "change_60m",
            "surge_detected"
        ]

        print(window[columns].round(2).to_string())

        print("\nEpisode statistics")

        print(
            "Valid observations:",
            window["value"].notna().sum()
        )

        print(
            "Missing observations:",
            window["value"].isna().sum()
        )

        print(
            "Maximum PM2.5:",
            window["value"].max()
        )

        print(
            "Median PM2.5:",
            window["value"].median()
        )

    print("\n" + "=" * 75)
    print("ALL SURGE EVENT INVESTIGATIONS COMPLETED")
    print("No database changes.")
    print("=" * 75)


if __name__ == "__main__":
    main()

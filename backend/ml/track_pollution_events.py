
import pandas as pd

from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)

from backend.ml.detect_pollution_surge import detect_surges


# ==================================================
# CONFIGURATION
# ==================================================

RECOVERY_RATIO = 1.20

# Require four consecutive 15-minute observations
# below the recovery threshold.
RECOVERY_CONSECUTIVE = 4

# These are experimental event-tracking settings,
# not official CPCB or WHO thresholds.


# ==================================================
# EVENT LIFECYCLE TRACKER
# ==================================================

def track_pollution_events(results):

    events = []

    active_event = None
    recovery_count = 0
    recovery_start = None

    for timestamp, row in results.iterrows():

        value = row["value"]
        surge_detected = bool(row["surge_detected"])

        # ------------------------------------------
        # START A NEW EVENT
        # ------------------------------------------

        if active_event is None:

            if not surge_detected:
                continue

            baseline = float(row["baseline_median"])

            active_event = {
                "start": timestamp,
                "baseline": baseline,
                "recovery_threshold": baseline * RECOVERY_RATIO,
                "peak": float(value),
                "peak_time": timestamp,
                "last_valid_time": timestamp,
                "valid_observations": 1,
                "missing_observations": 0,
                "max_increase": float(value - baseline),
                "recovery_start": None,
                "resolved_at": None,
                "status": "ACTIVE"
            }

            recovery_count = 0
            recovery_start = None

            continue

        # ------------------------------------------
        # HANDLE MISSING OBSERVATIONS
        # ------------------------------------------

        if pd.isna(value):

            active_event["missing_observations"] += 1

            recovery_count = 0
            recovery_start = None

            active_event["status"] = "DATA_GAP"

            continue

        value = float(value)

        active_event["last_valid_time"] = timestamp

        active_event["valid_observations"] += 1

        # ------------------------------------------
        # UPDATE EVENT PEAK
        # ------------------------------------------

        if value > active_event["peak"]:

            active_event["peak"] = value
            active_event["peak_time"] = timestamp

        increase = value - active_event["baseline"]

        active_event["max_increase"] = max(
            active_event["max_increase"],
            increase
        )

        # ------------------------------------------
        # RECOVERY MONITORING
        # ------------------------------------------

        recovery_threshold = active_event[
            "recovery_threshold"
        ]

        if value <= recovery_threshold:

            if recovery_count == 0:
                recovery_start = timestamp

            recovery_count += 1

            active_event["status"] = "RECOVERY_MONITORING"

            if recovery_count >= RECOVERY_CONSECUTIVE:

                active_event["recovery_start"] = recovery_start

                active_event["resolved_at"] = timestamp

                active_event["status"] = "RESOLVED"

                events.append(active_event.copy())

                active_event = None

                recovery_count = 0
                recovery_start = None

        else:

            recovery_count = 0
            recovery_start = None

            active_event["status"] = "ACTIVE"

    # ----------------------------------------------
    # SAVE UNRESOLVED EVENT
    # ----------------------------------------------

    if active_event is not None:

        events.append(active_event.copy())

    return events


# ==================================================
# REPORTING
# ==================================================

def print_event_report(events):

    print("\n" + "=" * 85)
    print("AIRWISE 360 - POLLUTION EVENT LIFECYCLE REPORT")
    print("=" * 85)

    if not events:

        print("\nNo pollution events detected.")

        return

    for number, event in enumerate(events, start=1):

        duration = (
            event["last_valid_time"] - event["start"]
        )

        percentage_increase = (
            (
                event["peak"] - event["baseline"]
            )
            / event["baseline"] * 100
            if event["baseline"] > 0
            else None
        )

        print(f"\nEVENT {number}")
        print("-" * 85)

        print("Start:", event["start"])

        print("Last valid observation:", event["last_valid_time"])

        print("Status:", event["status"])

        print(
            "Duration between first and last valid observation:",
            duration
        )

        print(
            "Baseline PM2.5:",
            round(event["baseline"], 2),
            "µg/m³"
        )

        print(
            "Recovery threshold:",
            round(event["recovery_threshold"], 2),
            "µg/m³"
        )

        print(
            "Peak PM2.5:",
            round(event["peak"], 2),
            "µg/m³"
        )

        print("Peak time:", event["peak_time"])

        print(
            "Maximum increase:",
            round(event["max_increase"], 2),
            "µg/m³"
        )

        if percentage_increase is not None:

            print(
                "Percentage increase:",
                round(percentage_increase, 2),
                "%"
            )

        print(
            "Valid observations:",
            event["valid_observations"]
        )

        print(
            "Missing observations:",
            event["missing_observations"]
        )

        print("Recovery started:", event["recovery_start"])

        print("Resolved at:", event["resolved_at"])


# ==================================================
# MAIN
# ==================================================

def main():

    print("\n" + "=" * 85)
    print("AIRWISE 360 - EVENT LIFECYCLE TRACKER")
    print("=" * 85)

    print("\n[1] Loading historical observations...")

    df = load_data()

    series = create_regular_series(df)

    print(
        "Valid observations:",
        series["value"].notna().sum()
    )

    print("\n[2] Detecting pollution surge triggers...")

    results = detect_surges(series)

    print(
        "Surge triggers:",
        int(results["surge_detected"].sum())
    )

    print("\n[3] Tracking event lifecycles...")

    events = track_pollution_events(results)

    print("\n[4] Event report")

    print_event_report(events)

    print("\n" + "=" * 85)
    print("EVENT TRACKING COMPLETED")
    print("Database unchanged.")
    print("No model trained.")
    print("Recovery settings are experimental.")
    print("=" * 85)


if __name__ == "__main__":
    main()


from backend.ml.prepare_forecasting_dataset import (
    load_data,
    create_regular_series
)

from backend.ml.detect_pollution_surge import detect_surges

from backend.ml.track_pollution_events import (
    track_pollution_events
)


# Current historical pipeline configuration.
SUPPORTED_LOCATION_ID = 6950
SUPPORTED_POLLUTANT = "pm25"
SUPPORTED_SENSOR_ID = 12235887


class PollutionEventService:

    def get_event_report(self, location_id, pollutant="pm25"):

        # ------------------------------------------
        # VALIDATE SUPPORTED DATA
        # ------------------------------------------

        if location_id != SUPPORTED_LOCATION_ID:
            raise ValueError(
                "Event analytics currently supports "
                "Jadavpur station only (location_id=6950)."
            )

        pollutant = pollutant.lower()

        if pollutant != SUPPORTED_POLLUTANT:
            raise ValueError(
                "Event analytics currently supports PM2.5 only."
            )

        # ------------------------------------------
        # LOAD HISTORICAL DATA
        # ------------------------------------------

        df = load_data()

        if df.empty:
            raise RuntimeError(
                "No historical observations available."
            )

        series = create_regular_series(df)

        if series.empty:
            raise RuntimeError(
                "Unable to construct historical time series."
            )

        # ------------------------------------------
        # DETECT SURGES
        # ------------------------------------------

        detection_results = detect_surges(series)

        # ------------------------------------------
        # TRACK EVENT LIFECYCLES
        # ------------------------------------------

        events = track_pollution_events(
            detection_results
        )

        # ------------------------------------------
        # BUILD API RESPONSE
        # ------------------------------------------

        formatted_events = []

        for number, event in enumerate(events, start=1):

            duration_minutes = (
                event["last_valid_time"] - event["start"]
            ).total_seconds() / 60

            baseline = event["baseline"]
            peak = event["peak"]

            percentage_increase = (
                ((peak - baseline) / baseline) * 100
                if baseline > 0
                else None
            )

            formatted_events.append({
                "event_id": number,

                "status": event["status"],

                "start": event["start"].isoformat(),

                "last_valid_observation": (
                    event["last_valid_time"].isoformat()
                ),

                "peak": round(peak, 2),

                "peak_time": event["peak_time"].isoformat(),

                "baseline": round(baseline, 2),

                "recovery_threshold": round(
                    event["recovery_threshold"], 2
                ),

                "maximum_increase": round(
                    event["max_increase"], 2
                ),

                "percentage_increase": (
                    round(percentage_increase, 2)
                    if percentage_increase is not None
                    else None
                ),

                "duration_minutes": round(
                    duration_minutes, 2
                ),

                "valid_observations": (
                    event["valid_observations"]
                ),

                "missing_observations": (
                    event["missing_observations"]
                ),

                "recovery_start": (
                    event["recovery_start"].isoformat()
                    if event["recovery_start"] is not None
                    else None
                ),

                "resolved_at": (
                    event["resolved_at"].isoformat()
                    if event["resolved_at"] is not None
                    else None
                )
            })

        # ------------------------------------------
        # EVENT COUNTS
        # ------------------------------------------

        total_events = len(formatted_events)

        resolved_events = sum(
            event["status"] == "RESOLVED"
            for event in formatted_events
        )

        active_events = sum(
            event["status"] in (
                "ACTIVE",
                "RECOVERY_MONITORING",
                "DATA_GAP"
            )
            for event in formatted_events
        )

        # ------------------------------------------
        # FINAL RESPONSE
        # ------------------------------------------

        return {
            "project": "AIRWISE 360°",

            "location_id": location_id,

            "station": "Jadavpur, Kolkata",

            "pollutant": pollutant,

            "unit": "µg/m³",

            "source": "OpenAQ historical sensor observations",

            "data_type": "ground_sensor_observations",

            "sensor_id": SUPPORTED_SENSOR_ID,

            "valid_observations": int(
                series["value"].notna().sum()
            ),

            "missing_observations": int(
                series["value"].isna().sum()
            ),

            "surge_triggers": int(
                detection_results["surge_detected"].sum()
            ),

            "total_events": total_events,

            "resolved_events": resolved_events,

            "unresolved_events": active_events,

            "events": formatted_events,

            "methodology": {
                "detection": "Rolling median and MAD-based surge detection",

                "recovery_ratio": 1.20,

                "recovery_consecutive_readings": 4,

                "recovery_interval_minutes": 15,

                "threshold_status": "Experimental",

                "official_aqi": False
            }
        }


event_service = PollutionEventService()

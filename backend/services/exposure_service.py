
from datetime import datetime
from statistics import mean
from zoneinfo import ZoneInfo

from backend.services.forecast_service import forecast_service


class ExposureService:

    TIMEZONE = ZoneInfo("Asia/Kolkata")

    SUPPORTED_ACTIVITIES = {
        "walking",
        "running",
        "cycling",
        "commuting"
    }

    POLLUTANT_FIELDS = {
        "pm25": "pm2_5",
        "pm10": "pm10"
    }

    def calculate_exposure(
        self,
        activity="walking",
        duration_minutes=30,
        sensitive_group=False,
        latitude=22.49929,
        longitude=88.36917,
        pollutant="pm25",
        window_hours=3
    ):

        # 1. Validate inputs
        if activity not in self.SUPPORTED_ACTIVITIES:
            raise ValueError(
                "Unsupported activity. Choose walking, running, cycling or commuting."
            )

        if (
            isinstance(duration_minutes, bool)
            or not isinstance(duration_minutes, int)
            or not 1 <= duration_minutes <= 480
        ):
            raise ValueError(
                "Duration must be an integer between 1 and 480 minutes."
            )

        if pollutant not in self.POLLUTANT_FIELDS:
            raise ValueError(
                "Unsupported pollutant. Choose pm25 or pm10."
            )

        if (
            isinstance(window_hours, bool)
            or not isinstance(window_hours, int)
            or not 1 <= window_hours <= 12
        ):
            raise ValueError(
                "window_hours must be an integer between 1 and 12."
            )

        if not isinstance(sensitive_group, bool):
            raise ValueError("sensitive_group must be True or False.")

        # 2. Fetch existing CAMS forecast
        forecast = forecast_service.get_forecast(
            latitude,
            longitude
        )

        hourly = forecast.get("hourly", {})

        times = hourly.get("time", [])

        field = self.POLLUTANT_FIELDS[pollutant]

        concentrations = hourly.get(field, [])

        if not times or not concentrations:
            return {
                "status": "no_forecast_data",
                "message": "The forecast API returned no hourly data."
            }

        # 3. Get current Kolkata time
        now = datetime.now(self.TIMEZONE)

        available = []

        # 4. Process future hourly observations
        for index, timestamp in enumerate(times):

            if index >= len(concentrations):
                continue

            value = concentrations[index]

            if value is None:
                continue

            try:
                forecast_time = datetime.fromisoformat(
                    timestamp
                )
            except (TypeError, ValueError):
                continue

            # Interpret timezone-naive timestamps as Kolkata time.
            if forecast_time.tzinfo is None:
                forecast_time = forecast_time.replace(
                    tzinfo=self.TIMEZONE
                )
            else:
                forecast_time = forecast_time.astimezone(
                    self.TIMEZONE
                )

            # Ignore past forecast hours.
            if forecast_time <= now:
                continue

            try:
                concentration = float(value)
            except (TypeError, ValueError):
                continue

            if concentration < 0:
                continue

            available.append({
                "timestamp": forecast_time.isoformat(),
                "datetime": forecast_time,
                "concentration": concentration
            })

        # 5. Sort forecast values chronologically
        available.sort(
            key=lambda item: item["datetime"]
        )

        if len(available) < window_hours:
            return {
                "status": "insufficient_forecast_data",
                "available_hours": len(available),
                "required_hours": window_hours,
                "message": (
                    "Not enough future hourly forecast values "
                    "are available for the requested window."
                ),
                "source": forecast.get("source"),
                "model": forecast.get("model")
            }

        # 6. Generate consecutive hourly windows
        candidates = []

        for index in range(
            len(available) - window_hours + 1
        ):

            window = available[
                index:index + window_hours
            ]

            values = [
                item["concentration"]
                for item in window
            ]

            # Ensure consecutive hourly observations.
            consecutive = all(
                (
                    window[i]["datetime"]
                    - window[i - 1]["datetime"]
                ).total_seconds() == 3600
                for i in range(1, len(window))
            )

            if not consecutive:
                continue

            average_concentration = mean(values)

            candidates.append({
                "start_time": window[0]["timestamp"],
                "end_time": window[-1]["timestamp"],
                "average_concentration": round(
                    average_concentration, 2
                ),
                "hourly_values": [
                    {
                        "timestamp": item["timestamp"],
                        "concentration": round(
                            item["concentration"], 2
                        )
                    }
                    for item in window
                ]
            })

        if not candidates:
            return {
                "status": "insufficient_forecast_data",
                "message": (
                    "No complete consecutive hourly forecast "
                    "window is available."
                )
            }

        # 7. Find comparatively lowest concentration window
        best_window = min(
            candidates,
            key=lambda item: item["average_concentration"]
        )

        average_concentration = (
            best_window["average_concentration"]
        )

        # 8. Simplified concentration-duration proxy
        exposure_proxy = round(
            average_concentration
            * (duration_minutes / 60),
            2
        )

        # 9. Generate recommendation
        recommendation = (
            "This is the comparatively lower-concentration "
            "forecast window among the available options. "
            "It is not a guarantee of safe air quality."
        )

        if sensitive_group:
            recommendation = (
                "This is a relatively lower-concentration "
                "forecast window, not a safety guarantee. "
                "Sensitive individuals should check official "
                "local AQI and medical advice before outdoor activity."
            )

        # 10. Return complete result
        return {
            "status": "success",
            "source": forecast.get("source"),
            "model": forecast.get("model"),
            "data_type": "modelled_air_quality_forecast",
            "location": forecast.get("location"),
            "timezone": "Asia/Kolkata",

            "activity": activity,
            "duration_minutes": duration_minutes,
            "pollutant": pollutant,
            "unit": "µg/m³",
            "sensitive_group": sensitive_group,

            "forecast_hours_available": len(available),
            "candidate_windows": len(candidates),

            "recommended_window": best_window,

            "exposure_proxy": {
                "value": exposure_proxy,
                "unit": "µg·h/m³",
                "formula": (
                    "average forecast concentration "
                    "× activity duration in hours"
                ),
                "warning": (
                    "Simplified concentration-duration proxy. "
                    "It is not an inhaled dose, AQI or medical risk estimate."
                )
            },

            "recommendation": recommendation,

            "disclaimer": (
                "Uses modelled CAMS forecast concentrations from "
                "Open-Meteo, not verified street-level sensor readings "
                "or official CPCB AQI. Forecast resolution and local "
                "conditions may differ."
            )
        }


exposure_service = ExposureService()


from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.services.forecast_service import forecast_service


# --------------------------------------------------
# CITY CONFIGURATION
# --------------------------------------------------

CITIES = {
    "Kolkata": {
        "latitude": 22.5726,
        "longitude": 88.3639
    },
    "Delhi": {
        "latitude": 28.6139,
        "longitude": 77.2090
    },
    "Mumbai": {
        "latitude": 19.0760,
        "longitude": 72.8777
    },
    "Bengaluru": {
        "latitude": 12.9716,
        "longitude": 77.5946
    }
}


POLLUTANTS = {
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "nitrogen_dioxide": "NO2",
    "sulphur_dioxide": "SO2",
    "carbon_monoxide": "CO",
    "ozone": "O3"
}


TIMEZONE = ZoneInfo("Asia/Kolkata")


# --------------------------------------------------
# CITY COMPARISON SERVICE
# --------------------------------------------------

class CityComparisonService:

    def __init__(self):
        self.forecasts = {}

    def _fetch_city_forecast(self, city, coordinates):

        result = forecast_service.get_forecast(
            latitude=coordinates["latitude"],
            longitude=coordinates["longitude"]
        )

        return city, result

    def _fetch_all_forecasts(self):

        results = {}
        errors = {}

        with ThreadPoolExecutor(max_workers=4) as executor:

            futures = {
                executor.submit(
                    self._fetch_city_forecast,
                    city,
                    coordinates
                ): city
                for city, coordinates in CITIES.items()
            }

            for future in as_completed(futures):

                city = futures[future]

                try:
                    name, forecast = future.result()
                    results[name] = forecast

                except Exception as error:
                    errors[city] = str(error)

        return results, errors

    def compare_cities(self):

        forecasts, errors = self._fetch_all_forecasts()

        if not forecasts:
            raise RuntimeError(
                "Unable to retrieve forecast data for any city"
            )

        # Find timestamps shared by all successfully retrieved cities.
        common_times = None

        for forecast in forecasts.values():

            times = set(forecast["hourly"]["time"])

            if common_times is None:
                common_times = times
            else:
                common_times &= times

        if not common_times:
            raise RuntimeError(
                "No common forecast timestamps available"
            )

        # Select the first common future timestamp.
        current_time = datetime.now(TIMEZONE).replace(tzinfo=None)

        future_times = sorted(
            timestamp
            for timestamp in common_times
            if datetime.fromisoformat(timestamp) > current_time
        )

        if not future_times:
            raise RuntimeError(
                "No future forecast timestamps available"
            )

        selected_time = future_times[0]

        city_results = {}

        for city, forecast in forecasts.items():

            hourly = forecast["hourly"]

            time_index = hourly["time"].index(selected_time)

            pollutant_values = {}

            for key, label in POLLUTANTS.items():

                values = hourly.get(key, [])

                value = (
                    values[time_index]
                    if time_index < len(values)
                    else None
                )

                pollutant_values[label] = value

            city_results[city] = {
                "coordinates": forecast["location"],
                "pollutants": pollutant_values,
                "model": forecast["model"],
                "source": forecast["source"]
            }

        # Rank cities independently for each pollutant.
        rankings = {}

        for pollutant in POLLUTANTS.values():

            available = [
                {
                    "city": city,
                    "value": data["pollutants"][pollutant]
                }
                for city, data in city_results.items()
                if data["pollutants"][pollutant] is not None
            ]

            available.sort(
                key=lambda item: item["value"]
            )

            rankings[pollutant] = {
                "lowest": available[0] if available else None,
                "highest": available[-1] if available else None,
                "cities_ranked": available
            }

        return {
            "project": "AIRWISE 360°",
            "comparison_type": "modelled_pollutant_forecast",
            "source": "Open-Meteo",
            "model": "CAMS Global",
            "timezone": "Asia/Kolkata",
            "forecast_timestamp": selected_time,
            "unit": "µg/m³",
            "cities_compared": list(city_results.keys()),
            "city_count": len(city_results),
            "city_data": city_results,
            "pollutant_rankings": rankings,
            "unavailable_cities": errors
        }


# --------------------------------------------------
# SERVICE INSTANCE
# --------------------------------------------------

city_comparison_service = CityComparisonService()

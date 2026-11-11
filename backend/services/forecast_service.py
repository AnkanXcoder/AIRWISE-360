
import requests


BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

KOLKATA_LATITUDE = 22.49929
KOLKATA_LONGITUDE = 88.36917


class ForecastService:

    def __init__(self):
        self.session = requests.Session()

    def get_forecast(
        self,
        latitude=KOLKATA_LATITUDE,
        longitude=KOLKATA_LONGITUDE
    ):

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "pm2_5,pm10,"
                "nitrogen_dioxide,"
                "sulphur_dioxide,"
                "carbon_monoxide,"
                "ozone"
            ),
            "forecast_days": 5,
            "timezone": "Asia/Kolkata",
            "domains": "cams_global"
        }

        try:
            response = self.session.get(
                BASE_URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            hourly = data.get("hourly")

            if not hourly or not hourly.get("time"):
                raise RuntimeError(
                    "Forecast data unavailable"
                )

            return {
                "source": "Open-Meteo",
                "data_type": "modelled_air_quality_forecast",
                "model": "CAMS Global",
                "location": {
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "timezone": data.get("timezone")
                },
                "units": data.get("hourly_units", {}),
                "hourly": hourly
            }

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"Forecast API request failed: {error}"
            ) from error


forecast_service = ForecastService()

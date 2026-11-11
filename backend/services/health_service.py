
class HealthService:

    ALLOWED_SOURCES = {
        "official_cpcb",
        "sensor_observation",
        "modeled_forecast",
        "unknown"
    }

    AQI_BANDS = [
        {"min": 0, "max": 50, "category": "Good"},
        {"min": 51, "max": 100, "category": "Satisfactory"},
        {"min": 101, "max": 200, "category": "Moderate"},
        {"min": 201, "max": 300, "category": "Poor"},
        {"min": 301, "max": 400, "category": "Very Poor"},
        {"min": 401, "max": 500, "category": "Severe"}
    ]

    HEALTH_GUIDANCE = {
        "Good": {
            "general": "Minimal impact. Normal outdoor activities are generally suitable.",
            "sensitive": "Sensitive individuals should follow their usual health precautions.",
            "activity": "Normal outdoor activity.",
            "ventilation": "Normal ventilation is generally suitable.",
            "mask": "A pollution mask is generally not necessary solely because of this AQI."
        },
        "Satisfactory": {
            "general": "Minor breathing discomfort may occur in sensitive individuals.",
            "sensitive": "People with asthma or other respiratory conditions should monitor symptoms.",
            "activity": "Normal outdoor activity; sensitive individuals should monitor symptoms.",
            "ventilation": "Normal ventilation is generally suitable.",
            "mask": "Consider a well-fitted particulate respirator if personally advised or needed."
        },
        "Moderate": {
            "general": "People with asthma, lung disease or heart disease may experience discomfort.",
            "sensitive": "Sensitive individuals should consider reducing prolonged or strenuous outdoor exertion.",
            "activity": "Prefer moderate activity and take breaks if discomfort occurs.",
            "ventilation": "Reduce outdoor air entry if pollution is elevated outdoors; maintain safe indoor ventilation.",
            "mask": "A well-fitted N95 or equivalent particulate respirator may reduce particle exposure outdoors."
        },
        "Poor": {
            "general": "Prolonged exposure may cause breathing discomfort in many people.",
            "sensitive": "Children, older adults and people with heart or lung conditions should limit prolonged outdoor exertion.",
            "activity": "Reduce prolonged outdoor exertion; move strenuous exercise indoors if indoor air is cleaner.",
            "ventilation": "Keep windows closed during high-pollution periods when indoor air is cleaner. Use filtration if available.",
            "mask": "Consider a well-fitted N95 or equivalent particulate respirator outdoors."
        },
        "Very Poor": {
            "general": "Prolonged exposure may cause respiratory illness in susceptible people.",
            "sensitive": "Sensitive groups should avoid strenuous outdoor activity and minimize exposure.",
            "activity": "Avoid strenuous outdoor exercise.",
            "ventilation": "Keep outdoor air entry limited when outdoor pollution is higher. Use indoor air filtration if available.",
            "mask": "Use a well-fitted N95 or equivalent particulate respirator if outdoor exposure is unavoidable."
        },
        "Severe": {
            "general": "Health effects may occur even among healthy people. Existing respiratory and cardiovascular conditions may be aggravated.",
            "sensitive": "Sensitive individuals should remain indoors as much as practical and follow medical advice.",
            "activity": "Avoid outdoor physical exertion. Reschedule outdoor activities where possible.",
            "ventilation": "Keep outdoor air entry limited when outdoor pollution is high. Use effective indoor filtration if available.",
            "mask": "Use a well-fitted N95 or equivalent particulate respirator if exposure outdoors cannot be avoided."
        }
    }

    def get_aqi_category(self, aqi):

        if aqi is None:
            return None

        if isinstance(aqi, bool) or not isinstance(aqi, (int, float)):
            raise ValueError("AQI must be a numeric value.")

        if not 0 <= aqi <= 500:
            raise ValueError("AQI must be between 0 and 500.")

        for band in self.AQI_BANDS:
            if band["min"] <= aqi <= band["max"]:
                return band["category"]

        return None

    def generate_guidance(
        self,
        official_aqi=None,
        source_type="unknown",
        sensitive_group=False,
        symptoms=False
    ):

        source_type = source_type.strip().strip('"').strip("'")

        if source_type not in self.ALLOWED_SOURCES:
            raise ValueError("Unsupported source_type.")

        if official_aqi is not None and source_type != "official_cpcb":
            raise ValueError(
                "An official AQI value can only be supplied "
                "with source_type=official_cpcb."
            )

        category = self.get_aqi_category(official_aqi)

        if category is None:
            guidance = {
                "general": (
                    "An official AQI category is unavailable. "
                    "Do not interpret individual pollutant readings "
                    "as an official AQI."
                ),
                "sensitive": (
                    "People with asthma, heart or lung conditions, "
                    "children and older adults should monitor "
                    "official local air-quality advisories."
                ),
                "activity": (
                    "Check the latest official local AQI before "
                    "planning prolonged or strenuous outdoor activity."
                ),
                "ventilation": (
                    "Use local outdoor air-quality information when "
                    "deciding when to ventilate indoor spaces."
                ),
                "mask": (
                    "If particulate pollution is elevated and outdoor "
                    "exposure is unavoidable, a well-fitted N95 or "
                    "equivalent respirator may reduce particle exposure."
                )
            }
            status = "official_aqi_unavailable"

        else:
            guidance = dict(self.HEALTH_GUIDANCE[category])
            status = "guidance_available"

        if sensitive_group:
            guidance["personalized_note"] = (
                "You selected a sensitive-group profile. "
                "Take extra care during outdoor exposure and follow "
                "your healthcare professional's advice."
            )

        if symptoms:
            guidance["symptom_warning"] = (
                "If you experience breathing difficulty, chest pain "
                "or severe symptoms, seek prompt medical attention. "
                "For a medical emergency, contact local emergency services."
            )

        return {
            "status": status,
            "source_type": source_type,
            "official_aqi": official_aqi,
            "aqi_category": category,
            "guidance": guidance,
            "disclaimer": (
                "General educational guidance, not a medical diagnosis. "
                "Only official CPCB AQI values are assigned AQI categories."
            )
        }


health_service = HealthService()

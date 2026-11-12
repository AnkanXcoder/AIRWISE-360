
# backend/services/cpcb_aqi_service.py

"""
AIRWISE 360 - CPCB National AQI Calculation Service

Calculates pollutant sub-indices using CPCB breakpoint interpolation.

Input records must contain:
{
    "pollutant": "pm25",
    "value": 45.0,
    "unit": "ug/m3",
    "timestamp": "2026-11-11T08:00:00+00:00"
}

Important:
- PM2.5, PM10, NO2, SO2, NH3, Pb: 24-hour averages.
- CO, O3: maximum rolling 8-hour averages.
- Minimum 16 valid hourly observations for a sub-index.
- Minimum 3 eligible pollutants for overall AQI.
- At least one of PM2.5 or PM10 is mandatory.
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math


# --------------------------------------------------
# CPCB BREAKPOINTS
# --------------------------------------------------

# Each breakpoint:
# (concentration_lower, concentration_upper,
#  aqi_lower, aqi_upper)

CPCB_BREAKPOINTS = {
    "pm25": {
        "unit": "ug/m3",
        "ranges": [
            (0, 30, 0, 50),
            (30, 60, 50, 100),
            (60, 90, 100, 200),
            (90, 120, 200, 300),
            (120, 250, 300, 400),
            (250, None, 400, 500),
        ],
    },

    "pm10": {
        "unit": "ug/m3",
        "ranges": [
            (0, 50, 0, 50),
            (50, 100, 50, 100),
            (100, 250, 100, 200),
            (250, 350, 200, 300),
            (350, 430, 300, 400),
            (430, None, 400, 500),
        ],
    },

    "no2": {
        "unit": "ug/m3",
        "ranges": [
            (0, 40, 0, 50),
            (40, 80, 50, 100),
            (80, 180, 100, 200),
            (180, 280, 200, 300),
            (280, 400, 300, 400),
            (400, None, 400, 500),
        ],
    },

    "so2": {
        "unit": "ug/m3",
        "ranges": [
            (0, 40, 0, 50),
            (40, 80, 50, 100),
            (80, 380, 100, 200),
            (380, 800, 200, 300),
            (800, 1600, 300, 400),
            (1600, None, 400, 500),
        ],
    },

    "co": {
        "unit": "mg/m3",
        "ranges": [
            (0, 1.0, 0, 50),
            (1.0, 2.0, 50, 100),
            (2.0, 10.0, 100, 200),
            (10.0, 17.0, 200, 300),
            (17.0, 34.0, 300, 400),
            (34.0, None, 400, 500),
        ],
    },

    "o3": {
        "unit": "ug/m3",
        "ranges": [
            (0, 50, 0, 50),
            (50, 100, 50, 100),
            (100, 168, 100, 200),
            (168, 208, 200, 300),
            (208, 748, 300, 400),
            (748, None, 400, 500),
        ],
    },

    "nh3": {
        "unit": "ug/m3",
        "ranges": [
            (0, 200, 0, 50),
            (200, 400, 50, 100),
            (400, 800, 100, 200),
            (800, 1200, 200, 300),
            (1200, 1800, 300, 400),
            (1800, None, 400, 500),
        ],
    },

    "pb": {
        "unit": "ug/m3",
        "ranges": [
            (0, 0.5, 0, 50),
            (0.5, 1.0, 50, 100),
            (1.0, 2.0, 100, 200),
            (2.0, 3.0, 200, 300),
            (3.0, 3.5, 300, 400),
            (3.5, None, 400, 500),
        ],
    },
}


# --------------------------------------------------
# AQI CATEGORIES
# --------------------------------------------------

AQI_CATEGORIES = [
    {
        "min": 0,
        "max": 50,
        "category": "Good",
        "description": "Minimal impact",
    },
    {
        "min": 51,
        "max": 100,
        "category": "Satisfactory",
        "description": "Minor breathing discomfort to sensitive people",
    },
    {
        "min": 101,
        "max": 200,
        "category": "Moderate",
        "description": "Breathing discomfort to sensitive groups",
    },
    {
        "min": 201,
        "max": 300,
        "category": "Poor",
        "description": "Breathing discomfort on prolonged exposure",
    },
    {
        "min": 301,
        "max": 400,
        "category": "Very Poor",
        "description": "Respiratory illness on prolonged exposure",
    },
    {
        "min": 401,
        "max": 500,
        "category": "Severe",
        "description": "Respiratory effects even on healthy people",
    },
]


# --------------------------------------------------
# POLLUTANT CONFIGURATION
# --------------------------------------------------

POLLUTANT_AVERAGING = {
    "pm25": 24,
    "pm10": 24,
    "no2": 24,
    "so2": 24,
    "nh3": 24,
    "pb": 24,
    "co": 8,
    "o3": 8,
}

MINIMUM_HOURLY_OBSERVATIONS = 16

REQUIRED_PARTICULATE = {"pm25", "pm10"}


# --------------------------------------------------
# UNIT NORMALIZATION
# --------------------------------------------------

UNIT_ALIASES = {
    "µg/m³": "ug/m3",
    "μg/m³": "ug/m3",
    "ug/m³": "ug/m3",
    "ug/m3": "ug/m3",
    "µg/m3": "ug/m3",
    "mg/m³": "mg/m3",
    "mg/m3": "mg/m3",
    "ppm": "ppm",
    "ppb": "ppb",
}


def normalize_unit(unit):
    if not unit:
        return None

    return UNIT_ALIASES.get(str(unit).strip().lower())


def normalize_pollutant(pollutant):
    if not pollutant:
        return None

    value = str(pollutant).strip().lower()

    aliases = {
        "pm2.5": "pm25",
        "pm_25": "pm25",
        "pm10": "pm10",
        "nitrogen dioxide": "no2",
        "no2": "no2",
        "sulfur dioxide": "so2",
        "sulphur dioxide": "so2",
        "so2": "so2",
        "carbon monoxide": "co",
        "co": "co",
        "ozone": "o3",
        "o3": "o3",
        "ammonia": "nh3",
        "nh3": "nh3",
        "lead": "pb",
        "pb": "pb",
    }

    return aliases.get(value, value)


def convert_to_cpcb_unit(value, unit, pollutant):
    """
    Convert only units that can be converted without assumptions.

    Gas concentrations reported in ppb or ppm are deliberately
    rejected because conversion to mass concentration depends on
    molecular weight, temperature and pressure.
    """

    target_unit = CPCB_BREAKPOINTS[pollutant]["unit"]
    source_unit = normalize_unit(unit)

    if source_unit is None:
        return None

    if source_unit == target_unit:
        return float(value)

    # Exact mass conversion.
    if source_unit == "mg/m3" and target_unit == "ug/m3":
        return float(value) * 1000

    if source_unit == "ug/m3" and target_unit == "mg/m3":
        return float(value) / 1000

    # Do not silently convert ppm/ppb.
    return None


# --------------------------------------------------
# TIMESTAMP PARSING
# --------------------------------------------------

def parse_timestamp(value):
    """Parse an ISO-8601 timestamp safely; reject missing/invalid values."""
    if value is None:
        return None

    if isinstance(value, datetime):
        timestamp = value
    else:
        value = str(value).strip()
        if not value or value.lower() in {"none", "null", "nan"}:
            return None
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    # Naive timestamps are ambiguous. Do not silently assume a timezone.
    if timestamp.tzinfo is None:
        return None

    return timestamp.astimezone(timezone.utc)


# --------------------------------------------------
# PREPARE HOURLY OBSERVATIONS
# --------------------------------------------------

def prepare_observations(records, now=None):

    now = now or datetime.now(timezone.utc)

    hourly_values = defaultdict(lambda: defaultdict(list))
    rejected = defaultdict(int)

    for record in records:

        pollutant = normalize_pollutant(
            record.get("pollutant")
        )

        if pollutant not in CPCB_BREAKPOINTS:
            continue

        try:
            value = float(record.get("value"))
        except (TypeError, ValueError):
            rejected[pollutant] += 1
            continue

        if not math.isfinite(value) or value < 0:
            rejected[pollutant] += 1
            continue

        # Support the normalized API field and common database field names.
        # The first non-empty field is used; missing timestamps are rejected.
        timestamp_value = (
            record.get("timestamp")
            or record.get("observed_at")
            or record.get("datetime")
        )
        timestamp = parse_timestamp(timestamp_value)

        if timestamp is None:
            rejected[pollutant] += 1
            continue

        age = (now - timestamp).total_seconds()

        # Reject future observations and observations
        # outside the preceding 24-hour period.
        if age < 0 or age > 24 * 3600:
            continue

        converted = convert_to_cpcb_unit(
            value,
            record.get("unit"),
            pollutant,
        )

        if converted is None:
            rejected[pollutant] += 1
            continue

        # Assign each reading to its UTC hour.
        hour = timestamp.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        hourly_values[pollutant][hour].append(converted)

    # Average multiple sensor observations within the same hour.
    hourly_averages = {}

    for pollutant, hours in hourly_values.items():
        hourly_averages[pollutant] = {
            hour: sum(values) / len(values)
            for hour, values in hours.items()
        }

    return hourly_averages, dict(rejected)


# --------------------------------------------------
# POLLUTANT AVERAGING
# --------------------------------------------------

def calculate_pollutant_average(
    hourly_values,
    pollutant,
    now=None,
):
    """
    Returns the required pollutant average.

    CO and O3:
        Maximum rolling 8-hour average within the last 24 hours.

    Other pollutants:
        Average across the preceding 24 hours.

    At least 16 valid hourly observations are required.
    """

    now = now or datetime.now(timezone.utc)

    values = hourly_values.get(pollutant, {})

    start = now - timedelta(hours=24)

    valid = {
        hour: value
        for hour, value in values.items()
        if start <= hour <= now
    }

    if len(valid) < MINIMUM_HOURLY_OBSERVATIONS:
        return {
            "available": False,
            "reason": "Insufficient hourly observations",
            "observations": len(valid),
            "required": MINIMUM_HOURLY_OBSERVATIONS,
        }

    if pollutant not in {"co", "o3"}:
        average = sum(valid.values()) / len(valid)

        return {
            "available": True,
            "average": average,
            "unit": CPCB_BREAKPOINTS[pollutant]["unit"],
            "observations": len(valid),
            "averaging_period_hours": 24,
        }

    # Maximum rolling 8-hour average.
    best_average = None

    for end_hour in sorted(valid):

        window_start = end_hour - timedelta(hours=7)

        window = [
            value
            for hour, value in valid.items()
            if window_start <= hour <= end_hour
        ]

        # Require all 8 hourly slots in this window.
        if len(window) != 8:
            continue

        average = sum(window) / 8

        if best_average is None or average > best_average:
            best_average = average

    if best_average is None:
        return {
            "available": False,
            "reason": "No complete rolling 8-hour average",
            "observations": len(valid),
            "required": 16,
        }

    return {
        "available": True,
        "average": best_average,
        "unit": CPCB_BREAKPOINTS[pollutant]["unit"],
        "observations": len(valid),
        "averaging_period_hours": 8,
    }


# --------------------------------------------------
# CPCB SUB-INDEX CALCULATION
# --------------------------------------------------

def calculate_sub_index(concentration, pollutant):

    config = CPCB_BREAKPOINTS.get(pollutant)

    if config is None:
        return None

    try:
        concentration = float(concentration)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(concentration) or concentration < 0:
        return None

    for blo, bhi, ilo, ihi in config["ranges"]:

        if bhi is None or concentration <= bhi:

            if concentration < blo:
                continue

            if bhi is None:
                return 500

            if bhi == blo:
                return int(ihi)

            sub_index = (
                ((ihi - ilo) / (bhi - blo))
                * (concentration - blo)
            ) + ilo

            return min(500, max(0, round(sub_index)))

    return 500


# --------------------------------------------------
# AQI CATEGORY
# --------------------------------------------------

def get_aqi_category(aqi):

    if aqi is None:
        return {
            "category": "Insufficient Data",
            "description": "AQI could not be calculated.",
        }

    for item in AQI_CATEGORIES:
        if item["min"] <= aqi <= item["max"]:
            return {
                "category": item["category"],
                "description": item["description"],
            }

    return {
        "category": "Insufficient Data",
        "description": "AQI is outside the supported range.",
    }


# --------------------------------------------------
# MAIN AQI CALCULATION
# --------------------------------------------------

def calculate_cpcb_aqi(records, now=None):

    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must include timezone information")

    now = now.astimezone(timezone.utc)

    hourly_values, rejected = prepare_observations(
        records,
        now,
    )

    pollutant_results = {}

    for pollutant in CPCB_BREAKPOINTS:

        average_result = calculate_pollutant_average(
            hourly_values,
            pollutant,
            now,
        )

        if not average_result["available"]:

            pollutant_results[pollutant] = {
                "available": False,
                **average_result,
            }

            continue

        concentration = average_result["average"]

        sub_index = calculate_sub_index(
            concentration,
            pollutant,
        )

        pollutant_results[pollutant] = {
            "available": True,
            "concentration": round(concentration, 3),
            "unit": average_result["unit"],
            "sub_index": sub_index,
            "averaging_period_hours": (
                average_result["averaging_period_hours"]
            ),
            "observations": average_result["observations"],
        }

    valid_pollutants = {
        pollutant: result
        for pollutant, result in pollutant_results.items()
        if result["available"]
    }

    particulate_available = bool(
        REQUIRED_PARTICULATE.intersection(valid_pollutants)
    )

    eligible = (
        len(valid_pollutants) >= 3
        and particulate_available
    )

    if eligible:

        dominant_pollutant = max(
            valid_pollutants,
            key=lambda pollutant: (
                valid_pollutants[pollutant]["sub_index"]
            ),
        )

        aqi = valid_pollutants[
            dominant_pollutant
        ]["sub_index"]

        category = get_aqi_category(aqi)

        status = "CALCULATED"

    else:

        dominant_pollutant = None
        aqi = None

        category = get_aqi_category(None)

        status = "INSUFFICIENT_DATA"

    return {
        "calculation_method": "CPCB National AQI",
        "status": status,
        "aqi": aqi,
        "category": category["category"],
        "health_description": category["description"],
        "dominant_pollutant": dominant_pollutant,
        "available_pollutants": len(valid_pollutants),
        "required_pollutants": 3,
        "particulate_requirement_met": particulate_available,
        "pollutants": pollutant_results,
        "rejected_observations": rejected,
        "calculated_at": now.isoformat(),
        "data_window": "Previous 24 hours",
        "source": "OpenAQ",
        "disclaimer": (
            "Calculated from available OpenAQ observations using "
            "CPCB breakpoint methodology. This is not an official "
            "CPCB-reported AQI. Sensor calibration, data completeness "
            "and measurement equivalence must be independently verified."
        ),
    }

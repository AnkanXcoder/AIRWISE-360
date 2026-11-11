
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from statistics import mean, median

from backend.database import get_historical_measurements


TIMEZONE = ZoneInfo("Asia/Kolkata")

SUPPORTED_POLLUTANTS = {
    "pm25", "pm10", "no2", "so2", "co", "o3"
}


class DiwaliImpactService:

    def __init__(self):
        self.default_city_locations = {
            "Kolkata": 6950,
            "Delhi": None
        }

    def _parse_timestamp(self, value):
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=TIMEZONE
            )

        return timestamp.astimezone(TIMEZONE)

    def _get_period_statistics(
        self,
        records,
        start_date,
        end_date,
        min_records,
        min_days
    ):
        period_records = []

        for record in records:
            observed_at = self._parse_timestamp(
                record["observed_at"]
            )

            if start_date <= observed_at.date() <= end_date:
                period_records.append({
                    "value": float(record["value"]),
                    "date": observed_at.date()
                })

        values = [
            item["value"] for item in period_records
        ]

        observation_days = sorted({
            item["date"] for item in period_records
        })

        coverage_sufficient = (
            len(values) >= min_records
            and len(observation_days) >= min_days
        )

        result = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "record_count": len(values),
            "observation_days": len(observation_days),
            "coverage_sufficient": coverage_sufficient,
            "statistics": None
        }

        if values:
            result["statistics"] = {
                "mean": round(mean(values), 2),
                "median": round(median(values), 2),
                "minimum": round(min(values), 2),
                "maximum": round(max(values), 2)
            }

        if not coverage_sufficient:
            result["coverage_message"] = (
                "Insufficient observations for a reliable "
                "period comparison."
            )

        return result

    def _percentage_change(self, baseline, comparison):
        if baseline is None or comparison is None:
            return None

        if baseline == 0:
            return None

        return round(
            ((comparison - baseline) / baseline) * 100,
            2
        )

    def _analyze_city(
        self,
        city,
        location_id,
        pollutant,
        diwali_start,
        diwali_end,
        pre_days,
        post_days,
        min_records,
        min_days
    ):

        if location_id is None:
            return {
                "status": "unavailable",
                "location_id": None,
                "message": (
                    "No verified monitoring location ID "
                    "configured for this city."
                ),
                "periods": {}
            }

        records = get_historical_measurements(
            location_id,
            pollutant,
            1000
        )

        if not records:
            return {
                "status": "no_data",
                "location_id": location_id,
                "message": (
                    "No historical observations found "
                    "for this monitoring location."
                ),
                "periods": {}
            }

        # Use one sensor consistently for this time series.
        sensor_groups = {}

        for record in records:
            sensor_id = record.get("sensor_id")

            if sensor_id is not None:
                sensor_groups.setdefault(
                    str(sensor_id), []
                ).append(record)

        if not sensor_groups:
            return {
                "status": "no_data",
                "location_id": location_id,
                "message": "No sensor-linked observations found.",
                "periods": {}
            }

        selected_sensor, selected_records = max(
            sensor_groups.items(),
            key=lambda item: len(item[1])
        )

        pre_start = diwali_start - timedelta(
            days=pre_days
        )
        post_end = diwali_end + timedelta(
            days=post_days
        )

        periods = {
            "pre_diwali": self._get_period_statistics(
                selected_records,
                pre_start,
                diwali_start - timedelta(days=1),
                min_records,
                min_days
            ),
            "during_diwali": self._get_period_statistics(
                selected_records,
                diwali_start,
                diwali_end,
                min_records,
                min_days
            ),
            "post_diwali": self._get_period_statistics(
                selected_records,
                diwali_end + timedelta(days=1),
                post_end,
                min_records,
                min_days
            )
        }

        pre_stats = periods["pre_diwali"]["statistics"]
        during_stats = periods["during_diwali"]["statistics"]
        post_stats = periods["post_diwali"]["statistics"]

        pre_valid = periods["pre_diwali"]["coverage_sufficient"]
        during_valid = periods["during_diwali"]["coverage_sufficient"]
        post_valid = periods["post_diwali"]["coverage_sufficient"]

        pre_mean = (
            pre_stats["mean"]
            if pre_valid and pre_stats else None
        )

        during_mean = (
            during_stats["mean"]
            if during_valid and during_stats else None
        )

        post_mean = (
            post_stats["mean"]
            if post_valid and post_stats else None
        )

        comparisons = {
            "during_vs_pre_percent": (
                self._percentage_change(pre_mean, during_mean)
            ),
            "post_vs_pre_percent": (
                self._percentage_change(pre_mean, post_mean)
            )
        }

        report_ready = (
            pre_valid and during_valid and post_valid
        )

        return {
            "status": (
                "complete" if report_ready
                else "insufficient_coverage"
            ),
            "location_id": location_id,
            "sensor_id": selected_sensor,
            "records_for_selected_sensor": len(
                selected_records
            ),
            "periods": periods,
            "comparisons": comparisons,
            "interpretation": (
                "Period comparisons are descriptive and do not "
                "establish that Diwali activities caused changes."
            )
        }

    def generate_report(
        self,
        diwali_start,
        diwali_end,
        pollutant="pm25",
        pre_days=7,
        post_days=7,
        min_records=3,
        min_days=2,
        city_locations=None
    ):

        if pollutant not in SUPPORTED_POLLUTANTS:
            raise ValueError(
                f"Unsupported pollutant: {pollutant}"
            )

        if diwali_end < diwali_start:
            raise ValueError(
                "Diwali end date cannot be before start date."
            )

        if pre_days < 1 or post_days < 1:
            raise ValueError(
                "Pre and post window lengths must be positive."
            )

        if min_records < 1 or min_days < 1:
            raise ValueError(
                "Minimum coverage requirements must be positive."
            )

        locations = (
            city_locations
            if city_locations is not None
            else self.default_city_locations
        )

        cities = {}

        for city, location_id in locations.items():
            cities[city] = self._analyze_city(
                city=city,
                location_id=location_id,
                pollutant=pollutant,
                diwali_start=diwali_start,
                diwali_end=diwali_end,
                pre_days=pre_days,
                post_days=post_days,
                min_records=min_records,
                min_days=min_days
            )

        return {
            "project": "AIRWISE 360°",
            "report_type": "diwali_pollution_impact",
            "data_type": "historical_sensor_observations",
            "timezone": "Asia/Kolkata",
            "pollutant": pollutant,
            "unit": "µg/m³",
            "event_window": {
                "start": diwali_start.isoformat(),
                "end": diwali_end.isoformat()
            },
            "configuration": {
                "pre_event_days": pre_days,
                "post_event_days": post_days,
                "minimum_records_per_period": min_records,
                "minimum_observation_days_per_period": min_days
            },
            "cities": cities,
            "methodology_note": (
                "Uses historical observations from one selected "
                "sensor per configured monitoring location. "
                "Insufficient periods are not used for percentage "
                "comparisons. Results show association over time, "
                "not proof of causation."
            )
        }


diwali_impact_service = DiwaliImpactService()

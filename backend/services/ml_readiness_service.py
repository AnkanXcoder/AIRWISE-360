
from datetime import datetime, timezone

import numpy as np
import pandas as pd


class MLReadinessService:

    # Configurable project-level thresholds.
    MIN_RECORDS = 500
    MIN_DAYS = 30
    MIN_SAMPLES_PER_SENSOR = 100
    MIN_OBSERVATION_DAYS = 20
    MIN_FORECASTING_SAMPLES = 500

    FREQUENCY = "15min"
    TIMEZONE = "Asia/Kolkata"

    def _profile_sensor(self, records, sensor_id):
        """Calculate historical data quality for one sensor."""

        sensor_records = [
            record for record in records
            if str(record.get("sensor_id")) == str(sensor_id)
        ]

        if not sensor_records:
            return {
                "sensor_id": sensor_id,
                "total_records": 0,
                "valid_records": 0,
                "observation_days": 0,
                "date_range_days": 0,
                "coverage_percentage": 0,
                "missing_intervals": 0,
                "longest_gap_hours": 0,
                "duplicate_timestamps": 0,
                "invalid_values": 0,
                "invalid_timestamps": 0,
                "future_timestamps": 0,
            }

        df = pd.DataFrame(sensor_records)

        df["timestamp"] = pd.to_datetime(
            df["observed_at"],
            utc=True,
            errors="coerce"
        )

        numeric_values = pd.to_numeric(
            df["value"],
            errors="coerce"
        )

        valid_value_mask = np.isfinite(numeric_values)

        invalid_values = int((~valid_value_mask).sum())
        invalid_timestamps = int(df["timestamp"].isna().sum())

        future_mask = (
            df["timestamp"].notna()
            & (df["timestamp"] > pd.Timestamp.now(tz="UTC"))
        )

        future_timestamps = int(future_mask.sum())

        valid_mask = (
            df["timestamp"].notna()
            & valid_value_mask
            & ~future_mask
        )

        valid_df = df.loc[valid_mask].copy()
        valid_df["value"] = numeric_values.loc[valid_mask]

        duplicate_count = int(
            valid_df["timestamp"].duplicated().sum()
        )

        valid_df = valid_df.drop_duplicates(
            subset=["timestamp"],
            keep="first"
        ).sort_values("timestamp")

        if valid_df.empty:
            return {
                "sensor_id": sensor_id,
                "total_records": len(sensor_records),
                "valid_records": 0,
                "observation_days": 0,
                "date_range_days": 0,
                "coverage_percentage": 0,
                "missing_intervals": 0,
                "longest_gap_hours": 0,
                "duplicate_timestamps": duplicate_count,
                "invalid_values": invalid_values,
                "invalid_timestamps": invalid_timestamps,
                "future_timestamps": future_timestamps,
            }

        timestamps = valid_df.set_index("timestamp")

        first_timestamp = timestamps.index.min()
        last_timestamp = timestamps.index.max()

        regular_series = timestamps["value"].asfreq(
            self.FREQUENCY
        )

        expected_intervals = len(regular_series)
        observed_intervals = int(regular_series.notna().sum())
        missing_intervals = int(regular_series.isna().sum())

        coverage = (
            observed_intervals / expected_intervals * 100
            if expected_intervals else 0
        )

        missing_mask = regular_series.isna()

        gap_groups = (
            missing_mask.ne(missing_mask.shift()).cumsum()
        )[missing_mask]

        gap_lengths = gap_groups.groupby(gap_groups).size()

        longest_gap_intervals = (
            int(gap_lengths.max()) if not gap_lengths.empty else 0
        )

        local_timestamps = timestamps.index.tz_convert(
            self.TIMEZONE
        )

        observation_days = int(
            local_timestamps.normalize().nunique()
        )

        date_range_days = (
            last_timestamp - first_timestamp
        ).total_seconds() / 86400

        return {
            "sensor_id": sensor_id,
            "total_records": len(sensor_records),
            "valid_records": observed_intervals,
            "observation_days": observation_days,
            "date_range_days": round(date_range_days, 2),
            "coverage_percentage": round(coverage, 2),
            "expected_intervals": expected_intervals,
            "missing_intervals": missing_intervals,
            "longest_gap_intervals": longest_gap_intervals,
            "longest_gap_hours": round(
                longest_gap_intervals * 15 / 60, 2
            ),
            "duplicate_timestamps": duplicate_count,
            "invalid_values": invalid_values,
            "invalid_timestamps": invalid_timestamps,
            "future_timestamps": future_timestamps,
        }

    def assess_readiness(self, records):
        """
        Assess historical data readiness.

        Retains the existing method name and top-level response
        fields for compatibility with the current API.
        """

        from backend.ml.prepare_forecasting_dataset import SENSOR_ID

        total_records = len(records)

        sensor_ids = {
            str(record.get("sensor_id"))
            for record in records
            if record.get("sensor_id") is not None
        }

        profile = self._profile_sensor(records, SENSOR_ID)

        checks = {
            "minimum_records": (
                profile["valid_records"] >= self.MIN_RECORDS
            ),
            "minimum_history": (
                profile["date_range_days"] >= self.MIN_DAYS
            ),
            "sensor_sample_size": (
                profile["valid_records"]
                >= self.MIN_SAMPLES_PER_SENSOR
            ),
            "observation_days": (
                profile["observation_days"]
                >= self.MIN_OBSERVATION_DAYS
            ),
            "valid_timestamps": (
                profile["invalid_timestamps"] == 0
            ),
            "no_future_timestamps": (
                profile["future_timestamps"] == 0
            ),
            "complete_values": (
                profile["invalid_values"] == 0
            ),
            "no_duplicate_sensor_timestamps": (
                profile["duplicate_timestamps"] == 0
            ),
        }

        ready = all(checks.values())

        return {
            "status": "ready" if ready else "insufficient_data",
            "ready": ready,
            "total_records": total_records,
            "valid_records": profile["valid_records"],
            "missing_values": profile["invalid_values"],
            "invalid_timestamps": profile["invalid_timestamps"],
            "future_timestamps": profile.get(
                "future_timestamps", 0
            ),
            "duplicate_timestamps": profile[
                "duplicate_timestamps"
            ],
            "sensor_count": len(sensor_ids),
            "observation_days": profile["observation_days"],
            "date_range_days": profile["date_range_days"],
            "selected_sensor": profile,
            "checks": checks,
            "thresholds": {
                "minimum_records": self.MIN_RECORDS,
                "minimum_history_days": self.MIN_DAYS,
                "minimum_samples_per_sensor": (
                    self.MIN_SAMPLES_PER_SENSOR
                ),
                "minimum_observation_days": (
                    self.MIN_OBSERVATION_DAYS
                ),
            },
            "message": (
                "Selected sensor meets initial historical "
                "data checks."
                if ready else
                "Selected sensor does not meet all historical "
                "data checks."
            ),
        }

    def assess_forecasting_readiness(self):
        """
        Assess the actual forecasting dataset using the
        existing AIRWISE feature and split functions.
        """

        from backend.ml.prepare_forecasting_dataset import (
            SENSOR_ID,
            POLLUTANT,
            LOCATION_ID,
            load_data,
            create_regular_series,
            build_forecasting_dataset,
            chronological_split,
        )

        raw_df = load_data()

        if raw_df.empty:
            return {
                "status": "insufficient_data",
                "ready": False,
                "production_ready": False,
                "message": "No forecasting observations available.",
            }

        series = create_regular_series(raw_df)

        dataset, feature_columns = build_forecasting_dataset(
            series
        )

        train, validation, test = chronological_split(dataset)

        missing_features = int(
            dataset[feature_columns].isna().sum().sum()
        )

        missing_targets = int(
            dataset["target_pm25_next_hour"].isna().sum()
        )

        chronological_order = (
            not train.empty
            and not validation.empty
            and not test.empty
            and train.index.max() < validation.index.min()
            and validation.index.max() < test.index.min()
        )

        sample_count = len(dataset)

        checks = {
            "minimum_forecasting_samples": (
                sample_count >= self.MIN_FORECASTING_SAMPLES
            ),
            "non_empty_training_set": not train.empty,
            "non_empty_validation_set": not validation.empty,
            "non_empty_test_set": not test.empty,
            "complete_features": missing_features == 0,
            "complete_targets": missing_targets == 0,
            "chronological_split": chronological_order,
        }

        experimental_ready = all(checks.values())

        return {
            "status": (
                "experimental"
                if experimental_ready
                else "insufficient_data"
            ),
            "ready": experimental_ready,
            "production_ready": False,
            "location_id": LOCATION_ID,
            "sensor_id": SENSOR_ID,
            "pollutant": POLLUTANT,
            "frequency": self.FREQUENCY,
            "forecast_horizon": "1 hour",
            "raw_observations": len(raw_df),
            "regular_intervals": len(series),
            "missing_intervals": int(
                series["value"].isna().sum()
            ),
            "usable_samples": sample_count,
            "feature_count": len(feature_columns),
            "feature_columns": feature_columns,
            "missing_feature_values": missing_features,
            "missing_target_values": missing_targets,
            "train_samples": len(train),
            "validation_samples": len(validation),
            "test_samples": len(test),
            "chronological_order": chronological_order,
            "checks": checks,
            "thresholds": {
                "minimum_forecasting_samples": (
                    self.MIN_FORECASTING_SAMPLES
                ),
            },
            "model_evaluation": {
                "baseline": "persistence",
                "status": "requires_evaluation",
                "production_eligible": False,
            },
            "message": (
                "Forecasting dataset is suitable for "
                "experimental evaluation. Production deployment "
                "is not approved."
                if experimental_ready else
                "Forecasting dataset does not meet all "
                "experimental readiness checks."
            ),
        }


ml_readiness_service = MLReadinessService()

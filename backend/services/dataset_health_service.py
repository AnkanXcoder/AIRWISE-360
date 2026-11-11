
import numpy as np

from backend.ml.prepare_forecasting_dataset import (
    LOCATION_ID,
    SENSOR_ID,
    POLLUTANT,
    load_data,
    create_regular_series,
    build_forecasting_dataset,
    chronological_split
)


INTERVAL_MINUTES = 15
RAPID_CHANGE_THRESHOLD = 10.0

TARGET_COLUMN = "target_pm25_next_hour"


class DatasetHealthService:

    def get_dataset_health(self, location_id):

        # --------------------------------------------------
        # 1. Validate requested location
        # --------------------------------------------------

        if location_id != LOCATION_ID:

            return {
                "status": "unsupported",
                "location_id": location_id,
                "message": (
                    "Dataset health monitoring is not configured "
                    "for this location."
                )
            }

        # --------------------------------------------------
        # 2. Load historical observations
        # --------------------------------------------------

        raw_df = load_data()

        if raw_df.empty:

            return {
                "status": "no_data",
                "location_id": location_id,
                "message": "No historical observations available."
            }

        series = create_regular_series(raw_df)

        if series.empty:

            return {
                "status": "no_data",
                "location_id": location_id,
                "message": "Unable to create a regular time series."
            }

        # --------------------------------------------------
        # 3. Calculate temporal data quality
        # --------------------------------------------------

        observed_mask = series["value"].notna()

        observed = int(observed_mask.sum())
        expected = len(series)
        missing = expected - observed

        coverage = (
            observed / expected * 100
            if expected > 0
            else 0
        )

        missing_mask = ~observed_mask

        group_ids = missing_mask.ne(
            missing_mask.shift(fill_value=False)
        ).cumsum()

        missing_groups = (
            series.loc[missing_mask]
            .groupby(group_ids[missing_mask])
            .size()
        )

        gap_durations = missing_groups * INTERVAL_MINUTES

        gap_count = len(gap_durations)

        longest_gap_minutes = (
            int(gap_durations.max())
            if gap_count > 0
            else 0
        )

        gaps_over_1_hour = int(
            (gap_durations > 60).sum()
        )

        gaps_over_6_hours = int(
            (gap_durations > 360).sum()
        )

        gaps_over_24_hours = int(
            (gap_durations > 1440).sum()
        )

        observation_days = int(
            series.loc[observed_mask]
            .index.normalize()
            .nunique()
        )

        # --------------------------------------------------
        # 4. Build forecasting dataset
        # --------------------------------------------------

        dataset, feature_columns = build_forecasting_dataset(
            series
        )

        if dataset.empty:

            return {
                "status": "insufficient_data",
                "location_id": location_id,
                "message": (
                    "Historical observations exist, but no "
                    "usable forecasting samples were generated."
                )
            }

        train, validation, test = chronological_split(dataset)

        # --------------------------------------------------
        # 5. Verify chronological ordering
        # --------------------------------------------------

        chronological = (
            not train.empty
            and not validation.empty
            and not test.empty
            and train.index.max() < validation.index.min()
            and validation.index.max() < test.index.min()
        )

        # --------------------------------------------------
        # 6. Feature and target completeness
        # --------------------------------------------------

        feature_missing = int(
            dataset[feature_columns].isna().sum().sum()
        )

        target_missing = int(
            dataset[TARGET_COLUMN].isna().sum()
        )

        # --------------------------------------------------
        # 7. Pollution trend distribution
        # --------------------------------------------------

        trend_counts = {}

        splits = {
            "training": train,
            "validation": validation,
            "test": test
        }

        for split_name, split_data in splits.items():

            if split_data.empty:

                trend_counts[split_name] = {
                    "total": 0,
                    "rapidly_rising": 0,
                    "rapidly_falling": 0,
                    "relatively_stable": 0
                }

                continue

            change_30m = (
                split_data["pm25_current"]
                - split_data["pm25_lag_30m"]
            )

            trend_counts[split_name] = {
                "total": len(split_data),
                "rapidly_rising": int(
                    (change_30m >= RAPID_CHANGE_THRESHOLD).sum()
                ),
                "rapidly_falling": int(
                    (change_30m <= -RAPID_CHANGE_THRESHOLD).sum()
                ),
                "relatively_stable": int(
                    (
                        (change_30m > -RAPID_CHANGE_THRESHOLD)
                        & (change_30m < RAPID_CHANGE_THRESHOLD)
                    ).sum()
                )
            }

        # --------------------------------------------------
        # 8. Concentration statistics
        # --------------------------------------------------

        values = series["value"].dropna()

        concentration = {
            "mean": round(float(values.mean()), 3),
            "median": round(float(values.median()), 3),
            "minimum": round(float(values.min()), 3),
            "maximum": round(float(values.max()), 3),
            "negative_values": int((values < 0).sum()),
            "non_finite_values": int(
                (~np.isfinite(values)).sum()
            )
        }

        # --------------------------------------------------
        # 9. Determine monitoring status
        # --------------------------------------------------

        monitoring_status = (
            "review_required"
            if (
                missing > 0
                or not chronological
                or feature_missing > 0
                or target_missing > 0
            )
            else "initial_checks_passed"
        )

        # --------------------------------------------------
        # 10. Return structured monitoring report
        # --------------------------------------------------

        return {
            "project": "AIRWISE 360°",
            "location_id": location_id,
            "sensor_id": SENSOR_ID,
            "pollutant": POLLUTANT,
            "data_source": "AIRWISE SQLite historical observations",

            "monitoring_status": monitoring_status,

            "data_quality": {
                "raw_observations": len(raw_df),
                "expected_intervals": expected,
                "observed_intervals": observed,
                "missing_intervals": missing,
                "coverage_percentage": round(coverage, 2),
                "observation_days": observation_days,
                "first_observation": str(series.index.min()),
                "last_observation": str(series.index.max()),
                "separate_gaps": gap_count,
                "longest_gap_minutes": longest_gap_minutes,
                "longest_gap_hours": round(
                    longest_gap_minutes / 60, 2
                ),
                "gaps_over_1_hour": gaps_over_1_hour,
                "gaps_over_6_hours": gaps_over_6_hours,
                "gaps_over_24_hours": gaps_over_24_hours
            },

            "concentration_statistics": concentration,

            "forecasting_dataset": {
                "total_samples": len(dataset),
                "training_samples": len(train),
                "validation_samples": len(validation),
                "test_samples": len(test),
                "feature_count": len(feature_columns),
                "feature_names": feature_columns,
                "missing_feature_values": feature_missing,
                "missing_target_values": target_missing,
                "chronological_ordering": chronological
            },

            "pollution_trends": trend_counts,

            "methodology": {
                "frequency": "15 minutes",
                "forecast_horizon": "1 hour",
                "rapid_change_threshold": (
                    RAPID_CHANGE_THRESHOLD
                ),
                "rapid_change_unit": (
                    "µg/m³ over 30 minutes"
                ),
                "threshold_type": "Experimental, not an official AQI threshold",
                "missing_data_policy": (
                    "Missing intervals are retained and not imputed."
                )
            }
        }


dataset_health_service = DatasetHealthService()

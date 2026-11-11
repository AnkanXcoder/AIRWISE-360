
from statistics import median, mean
from collections import defaultdict


class AnalyticsService:

    MIN_ANOMALY_SAMPLES = 8
    WINDOW_SIZE = 5
    Z_SCORE_THRESHOLD = 3.5
    FLATLINE_LENGTH = 5

    # ------------------------------------
    # VALUE EXTRACTION
    # ------------------------------------

    def _extract_values(self, measurements):
        values = []

        for item in measurements:
            value = item.get("value") if isinstance(item, dict) else item

            if value is not None:
                try:
                    values.append(float(value))
                except (TypeError, ValueError):
                    continue

        return values

    def _extract_valid_records(self, measurements):
        """
        Keep each valid measurement together with its timestamp.

        This prevents timestamps from becoming misaligned when
        invalid or missing values are skipped.
        """
        valid_records = []

        for original_index, item in enumerate(measurements):
            if isinstance(item, dict):
                raw_value = item.get("value")
                observed_at = item.get("observed_at")
            else:
                raw_value = item
                observed_at = None

            if raw_value is None:
                continue

            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            valid_records.append({
                "original_index": original_index,
                "value": value,
                "observed_at": observed_at,
            })

        return valid_records

    # ------------------------------------
    # ROBUST SCALE CALCULATION
    # ------------------------------------

    def _calculate_robust_score(self, current_value, history):
        """
        Calculate a robust anomaly score.

        Primary method:
            Modified Z-score using MAD.

        Fallback:
            IQR-based robust score when MAD is zero.

        If both MAD and IQR are zero, the score is undefined.
        In that case, do not create an anomaly solely because
        the current value differs from the median.
        """

        rolling_median = median(history)

        deviations = [
            abs(value - rolling_median)
            for value in history
        ]

        mad = median(deviations)

        if mad > 0:
            score = (
                0.6745 * (current_value - rolling_median) / mad
            )

            return {
                "rolling_median": rolling_median,
                "mad": mad,
                "score": score,
                "score_method": "modified_z_score",
            }

        # MAD is zero. Try an IQR-based fallback.
        sorted_history = sorted(history)

        q1 = self._percentile(sorted_history, 25)
        q3 = self._percentile(sorted_history, 75)

        iqr = q3 - q1

        if iqr > 0:
            robust_scale = iqr / 1.349

            score = (
                (current_value - rolling_median) / robust_scale
            )

            return {
                "rolling_median": rolling_median,
                "mad": mad,
                "score": score,
                "score_method": "iqr_fallback",
            }

        # No usable dispersion estimate.
        return {
            "rolling_median": rolling_median,
            "mad": mad,
            "score": None,
            "score_method": "undefined_zero_dispersion",
        }

    @staticmethod
    def _percentile(sorted_values, percentile):
        """
        Calculate a linearly interpolated percentile.
        Input must already be sorted.
        """
        if not sorted_values:
            return None

        if len(sorted_values) == 1:
            return sorted_values[0]

        position = (len(sorted_values) - 1) * percentile / 100

        lower_index = int(position)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        fraction = position - lower_index

        return (
            sorted_values[lower_index] * (1 - fraction)
            + sorted_values[upper_index] * fraction
        )

    # ------------------------------------
    # SPIKE DETECTION
    # ------------------------------------

    def detect_spikes(self, measurements):

        valid_records = self._extract_valid_records(measurements)

        values = [
            record["value"]
            for record in valid_records
        ]

        if len(values) < self.MIN_ANOMALY_SAMPLES:
            return {
                "status": "insufficient_data",
                "available_samples": len(values),
                "required_samples": self.MIN_ANOMALY_SAMPLES,
                "anomaly_count": 0,
                "anomalies": [],
                "flatline_detected": False,
                "longest_flatline": 0,
            }

        anomalies = []

        for index in range(self.WINDOW_SIZE, len(valid_records)):

            history_records = valid_records[
                index - self.WINDOW_SIZE:index
            ]

            history = [
                record["value"]
                for record in history_records
            ]

            current_record = valid_records[index]
            current_value = current_record["value"]

            score_result = self._calculate_robust_score(
                current_value,
                history,
            )

            rolling_median = score_result["rolling_median"]
            mad = score_result["mad"]
            modified_z = score_result["score"]

            # Do not flag observations when no valid dispersion
            # estimate can be calculated.
            if modified_z is None:
                continue

            if abs(modified_z) >= self.Z_SCORE_THRESHOLD:

                anomaly = {
                    "index": current_record["original_index"],
                    "value": round(current_value, 2),
                    "rolling_median": round(rolling_median, 2),
                    "mad": round(mad, 4),
                    "modified_z_score": round(modified_z, 2),
                    "score_method": score_result["score_method"],
                    "type": (
                        "potential_spike"
                        if current_value > rolling_median
                        else "potential_drop"
                    ),
                }

                # Use the original timestamp. Never manufacture
                # a timestamp from the array index.
                if current_record["observed_at"] is not None:
                    anomaly["observed_at"] = (
                        current_record["observed_at"]
                    )

                anomalies.append(anomaly)

        # ------------------------------------
        # FLATLINE DETECTION
        # ------------------------------------

        longest_flatline = 1
        current_flatline = 1

        for index in range(1, len(values)):

            if values[index] == values[index - 1]:
                current_flatline += 1
            else:
                current_flatline = 1

            longest_flatline = max(
                longest_flatline,
                current_flatline,
            )

        return {
            "status": "success",
            "available_samples": len(values),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "flatline_detected": (
                longest_flatline >= self.FLATLINE_LENGTH
            ),
            "longest_flatline": longest_flatline,
        }

    # ------------------------------------
    # HISTORICAL ANALYSIS
    # ------------------------------------

    def analyze_history(self, measurements):

        values = self._extract_values(measurements)

        if not values:
            return {
                "status": "no_data",
                "record_count": 0,
                "statistics": None,
                "sensor_analysis": {},
            }

        # Group records by sensor to avoid mixing time series.
        sensor_groups = defaultdict(list)

        for item in measurements:

            if not isinstance(item, dict):
                continue

            sensor_id = item.get("sensor_id")

            if sensor_id is not None and item.get("value") is not None:
                sensor_groups[str(sensor_id)].append(item)

        sensor_analysis = {}

        for sensor_id, records in sensor_groups.items():

            records = sorted(
                records,
                key=lambda item: item.get("observed_at") or "",
            )

            sensor_values = self._extract_values(records)

            if not sensor_values:
                continue

            sensor_analysis[sensor_id] = {
                "record_count": len(sensor_values),
                "first_observation": records[0].get("observed_at"),
                "last_observation": records[-1].get("observed_at"),
                "spike_detection": self.detect_spikes(records),
            }

        return {
            "status": "success",
            "record_count": len(values),
            "statistics": {
                "minimum": round(min(values), 2),
                "maximum": round(max(values), 2),
                "average": round(mean(values), 2),
                "median": round(median(values), 2),
            },
            "sensor_count": len(sensor_groups),
            "sensor_analysis": sensor_analysis,
            "data_note": (
                "Statistics describe the returned records. "
                "Observations from different sensors are not "
                "combined for anomaly detection."
            ),
        }


analytics_service = AnalyticsService()

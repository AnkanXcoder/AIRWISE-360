
import unittest
import pandas as pd

from backend.ml.track_pollution_events import (
    track_pollution_events
)


def make_test_data(values, triggers):

    index = pd.date_range(
        start="2026-11-10 10:00",
        periods=len(values),
        freq="15min",
        tz="Asia/Kolkata"
    )

    return pd.DataFrame(
        {
            "value": values,
            "surge_detected": triggers,
            "baseline_median": [50.0] * len(values)
        },
        index=index
    )


class TestPollutionEventTracker(unittest.TestCase):

    def test_no_surge(self):

        data = make_test_data(
            [50, 52, 55, 54],
            [False, False, False, False]
        )

        events = track_pollution_events(data)

        self.assertEqual(len(events), 0)

    def test_event_resolves_after_four_low_readings(self):

        data = make_test_data(
            [80, 70, 60, 60, 60, 60],
            [True, False, False, False, False, False]
        )

        events = track_pollution_events(data)

        self.assertEqual(len(events), 1)

        self.assertEqual(
            events[0]["status"],
            "RESOLVED"
        )

        self.assertEqual(
            events[0]["valid_observations"],
            6
        )

    def test_missing_data_resets_recovery_count(self):

        data = make_test_data(
            [80, 60, 60, None, 60, 60, 60, 60],
            [True, False, False, False, False, False, False, False]
        )

        events = track_pollution_events(data)

        self.assertEqual(len(events), 1)

        self.assertEqual(
            events[0]["status"],
            "RESOLVED"
        )

        self.assertEqual(
            events[0]["missing_observations"],
            1
        )

        # Recovery starts after the missing observation.
        self.assertEqual(
            events[0]["recovery_start"],
            data.index[4]
        )

    def test_event_stays_active_without_four_low_readings(self):

        data = make_test_data(
            [80, 60, 60, 60],
            [True, False, False, False]
        )

        events = track_pollution_events(data)

        self.assertEqual(len(events), 1)

        self.assertEqual(
            events[0]["status"],
            "RECOVERY_MONITORING"
        )

        self.assertIsNone(events[0]["resolved_at"])

    def test_peak_is_tracked_correctly(self):

        data = make_test_data(
            [80, 120, 110, 60, 60, 60, 60],
            [True, False, False, False, False, False, False]
        )

        events = track_pollution_events(data)

        self.assertEqual(
            events[0]["peak"],
            120.0
        )

        self.assertEqual(
            events[0]["peak_time"],
            data.index[1]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)

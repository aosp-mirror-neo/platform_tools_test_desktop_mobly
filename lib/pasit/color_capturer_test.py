# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for color_capturer.py."""

import itertools
import unittest
from unittest import mock

from lib.pasit import color_capturer
from lib.utils import image


class ExposureStabilityTrackerTest(unittest.TestCase):
  """Unit tests for ExposureStabilityTracker."""

  def setUp(self):
    super().setUp()
    self.tracker = color_capturer.ExposureStabilityTracker()

  def test_exposure_stability_tracker_converges(self):
    # 1st sample: OVER
    self.tracker.add_sample({'over': 10.0, 'under': 5.0})
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.OVEREXPOSED
    )

    # 2nd sample: stable with 1st, but only 2 samples so far
    self.tracker.add_sample({'over': 10.5, 'under': 5.2})
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.OVEREXPOSED
    )

    # 3rd sample: stable with 2nd, now 3 samples
    self.tracker.add_sample({'over': 11.0, 'under': 5.5})
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.BALANCED
    )

  def test_exposure_stability_tracker_unstable(self):
    # 1st: {over: 10}
    self.tracker.add_sample({'over': 10.0})
    # 2nd: {over: 13} -> diff 3.0 (> 2.0)
    self.tracker.add_sample({'over': 13.0})
    # 3rd: {over: 14} -> stable with 2nd, but 1st vs 2nd was unstable
    self.tracker.add_sample({'over': 14.0})

    # Even though 2nd and 3rd are close (diff 1.0), 1st and 2nd were not.
    # So it should not be BALANCED.
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.OVEREXPOSED
    )

  def test_get_feedback_filters_out_non_feedback_keys(self):
    # 1st: {over: 10, 'RED': 90}
    self.tracker.add_sample({'over': 10.0, 'RED': 90.0})
    # 2nd: {over: 10.5, 'RED': 50} -> RED changed a lot, but should be ignored
    self.tracker.add_sample({'over': 10.5, 'RED': 50.0})
    # 3rd: {over: 11.0, 'RED': 10}
    self.tracker.add_sample({'over': 11.0, 'RED': 10.0})

    # 'over' is stable (values 10, 10.5, 11.0, max diff 0.5 < 2.0)
    # 'RED' is unstable if it were checked, but it should be filtered out.
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.BALANCED
    )

  def test_get_feedback_handles_missing_keys(self):
    # 1st sample has 'under'
    self.tracker.add_sample({'under': 10.0})
    # 2nd sample missing 'under' (implicitly 0.0) -> diff 10.0 (> 2.0)
    self.tracker.add_sample({'over': 1.0})
    # 3rd sample has 'under' = 1.0 -> diff 1.0 with 2nd sample (under=0.0)
    self.tracker.add_sample({'over': 1.5, 'under': 1.0})

    # Sequence for 'under': 10.0, 0.0, 1.0. Diffs: 10.0 and 1.0.
    # 10.0 is > 2.0, so unstable.
    self.assertNotEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.BALANCED
    )

  def test_get_feedback_all_feedback_keys_must_be_stable(self):
    # 1st
    self.tracker.add_sample({'over': 10.0, 'under': 10.0})
    # 2nd: 'over' stable, 'under' unstable (diff 3.0)
    self.tracker.add_sample({'over': 10.5, 'under': 13.0})
    # 3rd: both stable with previous
    self.tracker.add_sample({'over': 11.0, 'under': 14.0})

    # overall unstable because 'under' had a jump between 1st and 2nd.
    self.assertNotEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.BALANCED
    )

  def test_get_feedback_not_balanced_if_stuck_at_100_percent_over(self):
    # 3 samples all 100% overexposed
    for _ in range(3):
      self.tracker.add_sample({'over': 100.0, 'under': 0.0})

    # This should NOT be balanced, it should be OVEREXPOSED
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.OVEREXPOSED
    )

  def test_get_feedback_not_balanced_if_stuck_at_100_percent_under(self):
    # 3 samples all 100% underexposed
    for _ in range(3):
      self.tracker.add_sample({'over': 0.0, 'under': 100.0})

    # This should NOT be balanced, it should be UNDEREXPOSED
    self.assertEqual(
        self.tracker.get_feedback(),
        color_capturer.ExposureFeedback.UNDEREXPOSED,
    )

  def test_get_feedback_not_balanced_if_above_threshold(self):
    # 3 samples all 21% overexposed (above 20% threshold)
    for _ in range(3):
      self.tracker.add_sample({'over': 21.0, 'under': 5.0})

    # This should NOT be balanced, it should be OVEREXPOSED
    self.assertEqual(
        self.tracker.get_feedback(), color_capturer.ExposureFeedback.OVEREXPOSED
    )


class ColorCapturerTest(unittest.TestCase):
  """Unit tests for color_capturer.py."""

  def setUp(self):
    super().setUp()
    self.mock_passport = mock.MagicMock()

  def test_binary_search_exposure_converges(self):
    gen = color_capturer.binary_search_exposure(0, 1000, tolerance=10)

    # First suggestion: (0 + 1000) / 2 = 500
    val = next(gen)
    self.assertEqual(val, 500)

    # Feed back overexposed
    val = gen.send(color_capturer.ExposureFeedback.OVEREXPOSED)
    # Next suggestion: (0 + 500) / 2 = 250
    self.assertEqual(val, 250)

    # Feed back underexposed
    val = gen.send(color_capturer.ExposureFeedback.UNDEREXPOSED)
    # Next suggestion: (250 + 500) / 2 = 375
    self.assertEqual(val, 375)

    # Feed back balanced
    with self.assertRaises(StopIteration):
      gen.send(color_capturer.ExposureFeedback.BALANCED)

  def test_matched_color_iterator_default_masks(self):
    # Mocking feedback: 3 identical samples to reach BALANCED
    self.mock_passport.analyze_hsv.return_value = {
        image.NamedColor.RED.name: 90.0,
        color_capturer.ExposureFeedback.OVEREXPOSED.value: 5.0,
        color_capturer.ExposureFeedback.UNDEREXPOSED.value: 5.0,
    }

    iterator = color_capturer.MatchedColorIterator(
        passport=self.mock_passport,
        camera_id='camera0',
        log_path='/tmp',
        min_exposure=0,
        max_exposure=1000,
    )

    # 1st iteration: UNDER (since over=5, under=5, default to UNDER)
    color = next(iterator)
    self.assertEqual(color, image.NamedColor.RED)
    self.assertEqual(
        iterator.exposure_feedback, color_capturer.ExposureFeedback.UNDEREXPOSED
    )

    # 2nd iteration: UNDER
    color = next(iterator)
    self.assertEqual(color, image.NamedColor.RED)
    self.assertEqual(
        iterator.exposure_feedback, color_capturer.ExposureFeedback.UNDEREXPOSED
    )

    # 3rd iteration: BALANCED
    color = next(iterator)
    self.assertEqual(color, image.NamedColor.RED)
    self.assertEqual(
        iterator.exposure_feedback, color_capturer.ExposureFeedback.BALANCED
    )

  def test_matched_color_iterator_overexposed_wins(self):
    # Red is 45%, but Overexposed is 55%
    self.mock_passport.analyze_hsv.return_value = {
        image.NamedColor.RED.name: 45.0,
        color_capturer.ExposureFeedback.OVEREXPOSED.value: 55.0,
    }

    iterator = color_capturer.MatchedColorIterator(
        passport=self.mock_passport,
        camera_id='camera0',
        log_path='/tmp',
        min_exposure=0,
        max_exposure=1000,
    )

    color = next(iterator)
    self.assertIsNone(color)

  def test_matched_color_iterator_color_wins_over_exposure(self):
    # Red is 79%, but Overexposed is 50%
    self.mock_passport.analyze_hsv.return_value = {
        image.NamedColor.RED.name: 79.0,
        color_capturer.ExposureFeedback.OVEREXPOSED.value: 50.0,
    }

    iterator = color_capturer.MatchedColorIterator(
        passport=self.mock_passport,
        camera_id='camera0',
        log_path='/tmp',
        min_exposure=0,
        max_exposure=1000,
    )

    color = next(iterator)
    self.assertEqual(color, image.NamedColor.RED)
    # Even though it matched RED, the feedback should still be OVEREXPOSED
    self.assertEqual(
        iterator.exposure_feedback, color_capturer.ExposureFeedback.OVEREXPOSED
    )

  def test_get_camera_exposure_success(self):
    # Mocking feedback:
    # 500us -> over (1st sample)
    # 250us -> over (2nd sample)
    # 125us -> stable sequence: s1(125), s2(125), s3(125) -> balanced
    self.mock_passport.analyze_hsv.side_effect = [
        {'over': 80.0},  # 500us
        {'over': 80.0},  # 250us
        {'over': 5.0},  # 125us
        {'over': 5.0},  # 62us
        {'over': 5.0},  # 31us
    ]

    exposure = color_capturer.get_camera_exposure(
        camera_id='camera0',
        passport=self.mock_passport,
        log_path='/tmp',
        min_exposure=0,
        max_exposure=1000,
    )

    self.assertEqual(exposure, 31)
    self.assertEqual(self.mock_passport.analyze_hsv.call_count, 5)

  def test_get_camera_exposure_fails_to_converge_max_iterations(self):
    # Always overexposed but never settles
    self.mock_passport.analyze_hsv.side_effect = itertools.cycle([
        {'over': 15.0, 'black': 50.0},  # over
        {'over': 20.0, 'black': 50.0},  # over
    ])
    with self.assertRaisesRegex(
        RuntimeError, 'Could not find optimal exposure'
    ):
      color_capturer.get_camera_exposure(
          camera_id='camera0',
          passport=self.mock_passport,
          log_path='/tmp',
          min_exposure=0,
          max_exposure=1000000,  # large range to ensure we hit max iterations
          camera_capture_prefix='test_fail',
      )
    # 15 iterations + 1 final call with built-in auto-exposure
    self.assertEqual(self.mock_passport.analyze_hsv.call_count, 16)


if __name__ == '__main__':
  unittest.main()

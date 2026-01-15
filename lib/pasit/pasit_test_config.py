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

"""Various config definitions for PASIT Mobly tests."""

import enum


class RebootPolicy(enum.Enum):
  """Reboot policy for the DUT."""

  NONE = 0
  # if set then reboot the DUT during teardown_test if a test fails
  ON_FAIL = 1
  # if set then reboot the DUT during teardown_test (after each test that is
  # executed)
  ON_TEARDOWN_TEST = 2


class BugReportPolicy(str, enum.Enum):
  """Bug report policy for the DUT.

  The string value represents the value used in the test config and allows for
  overriding the policy via the mobly config at runtime.
  """

  NONE = 'none'
  ON_FAIL = 'on_fail'
  ALL = 'all'

  def should_collect_bugreport(self, test_failed: bool) -> bool:
    """Returns whether a bug report should be collected."""
    match self:
      case BugReportPolicy.ALL:
        return True
      case BugReportPolicy.ON_FAIL:
        return test_failed
      case BugReportPolicy.NONE:
        return False


class FailurePolicy(str, enum.Enum):
  """Test failure policy for the DUT."""

  CONTINUE = 'continue'
  DROP_TO_INTERPRETER = 'drop_to_interpreter'

  def should_drop_to_interpreter(self) -> bool:
    """Returns whether the test should drop to interpreter."""
    return self == FailurePolicy.DROP_TO_INTERPRETER


class ScreenRecordingPolicy(enum.Enum):
  """Screen recording policy for the DUT."""

  ENABLED = 1
  DISABLED = 0

  def should_record(self) -> bool:
    """Returns whether the screen should be recorded."""
    match self:
      case ScreenRecordingPolicy.ENABLED:
        return True
      case ScreenRecordingPolicy.DISABLED:
        return False

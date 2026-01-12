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

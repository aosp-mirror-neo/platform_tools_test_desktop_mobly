# Copyright 2025 Google LLC
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

"""A module to manage compliance tests based on VESA standards.

This module provides classes to represent and manage compliance tests,
including their IDs, VESA references, and descriptions. It allows for
grouping tests by UCD (Universal Compliance Document) and provides methods
to retrieve tests by their VESA references.
"""

import dataclasses
from chromiumos.test.lab.api.passport import video_tester_service_pb2


@dataclasses.dataclass(frozen=True)
class Test:
  """Represents a single compliance test matching VESA tests."""

  id: int  # The ID used by UCD API (e.g., 0, 1, 2...)
  reference: str  # The vesa reference (e.g., "4.2.1.1")
  description: str


@dataclasses.dataclass(frozen=True)
class TestGroup:
  """Represents a group of compliance tests, grouped by UCD."""

  group_id: video_tester_service_pb2.ComplianceTestGroup
  name: str
  # Dictionary mapping VESA reference to Test object.
  tests: dict[str, Test]
  # Dictionary mapping test id to Test object.
  tests_by_id: dict[int, Test]

  @classmethod
  def from_list(
      cls,
      group_id: video_tester_service_pb2.ComplianceTestGroup,
      name: str,
      test_list: list[tuple[int, str, str]],
  ) -> "TestGroup":
    """Helper method to create a TestGroup from a list of test details.

    Args:
        group_id: The ID for the group used by the hardware API.
        name: The test group name
        test_list: A list of tuples, where each tuple contains the test ID, VESA
          reference, and description.

    Returns:
        A TestGroup object.

    Raises:
        ValueError: If duplicate test references are found within the group.
    """
    tests_dict = {}
    tests_by_id_dict = {}
    for test_id, reference, description in test_list:
      if reference in tests_dict:
        # Ensure references are unique within a group
        raise ValueError(
            f"Duplicate test reference '{reference}' found in group '{name}'"
        )
      test = Test(
          id=test_id, reference=reference, description=description
      )
      tests_dict[reference] = test
      tests_by_id_dict[test_id] = test
    return cls(
        group_id=group_id,
        name=name,
        tests=tests_dict,
        tests_by_id=tests_by_id_dict,
    )

  def get_test_by_reference(self, reference: str) -> Test | None:
    """Retrieves a test from the group using its reference string."""
    return self.tests.get(reference)

  def get_test_by_id(self, test_id: int) -> Test | None:
    """Retrieves a test from the group using its id."""
    return self.tests_by_id.get(test_id)

  def get_video_tester_group_and_test_ids(
      self, references: list[str]
  ) -> list[video_tester_service_pb2.ComplianceTestVideoTester]:
    """Translates a list of test references into a list of (group_id, test_id) tuples.

    Args:
        references: A list of test reference strings (e.g., ["4.2.1.1",
          "4.2.1.4"]).

    Returns:
        A list of ComplianceTestVideoTester (group id and test id) objects.

    Raises:
        ValueError: If any reference is not found in the specified group.
    """
    tester_tests = []
    for reference in references:
      test = self.get_test_by_reference(reference)
      if test is None:
        raise ValueError(
            f"Test reference '{reference}' not found in group '{self.name}' "
            f"(ID: {self.group_id})"
        )
      tester_tests.append(
          video_tester_service_pb2.ComplianceTestVideoTester(
              group_id=self.group_id, test_id=test.id
          )
      )

    return tester_tests

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

"""Base test class for tests requiring connected displays."""

import dataclasses
import logging
import os
import re
import sys
from typing import Sequence

from display.utils import connected_display_manager
from display.utils import modetest_helper
from lib.pasit import pasit_test
from lib.pasit.base import base_pasit_device
from mobly import asserts
from mobly import base_instrumentation_test
from mobly import records
from mobly import signals


@dataclasses.dataclass
class GTestSuite:
  name: str
  methods: Sequence[str]


class WrappedDisplayBaseTest(
    pasit_test.PasitTestClass,
    base_instrumentation_test.InstrumentationTestMixin,
):
  """Base class that provides utilities for running wrapped display tests."""
  DEFAULT_DATA_PATH: str = os.path.dirname(os.path.abspath(sys.argv[0]))
  DEVICE_TMP_DIR: str = '/data/local/tmp'

  display_manager: connected_display_manager.DisplayManager | None = None
  num_default_displays: int = 1
  max_tested_displays: int = 0

  apks: Sequence[str] = []
  native_modules: Sequence[str] = []
  stop_services: Sequence[str] = []

  def setup_class(self):
    super().setup_class()

    if self.passport_host:
      # Check if any video tester is present in the topology
      if self.passport_host.video_tester_client.get_connected_video_testers():
        logging.info('Video tester detected. Using VideoTesterDisplayManager.')
        self.display_manager = (
            connected_display_manager.VideoTesterDisplayManager(
                self.passport_host, self.dut
            )
        )
      else:
        logging.info('No video tester detected. Using SwitchDisplayManager.')
        self.display_manager = connected_display_manager.SwitchDisplayManager(
            self.passport_host
        )
      self.display_manager.Reset()
    else:
      logging.info(
          'No Passport topology. Assuming static display connected.'
      )
      self.max_tested_displays = self.num_default_displays

    for module in self.native_modules:
      path = self.get_resource_path(module)
      device_path = self.get_install_path(module)
      self.install_native_binary(path, device_path)
    for apk in self.apks:
      path = self.get_resource_path(apk, extension='.apk')
      self.install_apk(path)
    self._check_display_count()

  def _check_display_count(self):
    max_crtc_on_dut = modetest_helper.get_crtcs_count(self.dut)
    self.max_tested_displays = min(
        self.display_manager.GetMaxDisplays(),
        max_crtc_on_dut - 1,  # 1 is used by eDP
    )
    logging.info('max_tested_displays: %d', self.max_tested_displays)
    asserts.assert_greater(
        self.max_tested_displays,
        0,
        'No displays are supported by the system: max_crtc_on_dut:'
        f'{max_crtc_on_dut}, max_supported_displays:'
        f'{self.display_manager.GetMaxDisplays()}',
    )

  def setup_test(self):
    super().setup_test()
    if self.display_manager and self.num_default_displays > 0:
      logging.info('Connecting %d display(s).', self.num_default_displays)
      self.display_manager.ConnectDisplays(self.num_default_displays)

    for service in self.stop_services:
      try:
        self.dut.shell(['stop', service])
      except base_pasit_device.ShellError as e:
        logging.warning('failed to stop service: %s: %s', service, e)

  def teardown_test(self):
    if self.display_manager:
      logging.info('Resetting display manager.')
      self.display_manager.Reset()

    for service in self.stop_services:
      try:
        self.dut.shell(['start', service])
      except base_pasit_device.ShellError as e:
        logging.warning('failed to start service: %s: %s', service, e)

    super().teardown_test()

  def get_resource_path(self, resource_name: str, extension: str = '') -> str:
    """Gets the absolute path to a test resource.

    Args:
      resource_name: Name of the resource.
      extension: Optional extension to append to the resource name.

    Returns:
      The absolute path to the resource.

    Raises:
      signals.TestError: If the resource cannot be found.
    """
    path = os.path.join(self.DEFAULT_DATA_PATH, resource_name + extension)

    files = self.user_params.get('files', {})
    if resource_name in files:
      path = files[resource_name][0]

    if not os.path.exists(path):
      raise signals.TestError(
          f'Unable to find binary at path "{resource_name}"')
    return path

  def get_install_path(self, module_name: str) -> str:
    """Gets the installation path for a module on the device.

    Args:
      module_name: Name of the module.

    Returns:
      The path where the module should be installed on the device.
    """
    return os.path.join(self.DEVICE_TMP_DIR, module_name)

  def install_apk(self, path: str) -> None:
    """Installs an APK on the DUT.

    Args:
      path: Path to the APK file.
    """
    logging.info('Installing apk: %s from: %s', os.path.basename(path), path)
    self.dut.controller.adb.install(['-r', '-g', path])

  def install_native_binary(self, path: str, device_path: str) -> None:
    """Installs a native binary on the DUT.

    Args:
      path: Path to the binary on the host.
      device_path: Destination path on the device.
    """
    logging.info(
        'Installing native binary %s from %s at %s',
        os.path.basename(path),
        path,
        device_path,
    )
    self.dut.shell(['mkdir', '-p', os.path.dirname(device_path)])
    self.dut.controller.adb.push([path, device_path])
    self.dut.shell(['chmod', '+x', device_path])

  def run_all_gtest_test(self, path) -> bool:
    """Runs all tests in a GTest binary and creates a record for each subtest.

    Args:
      path: Path to the GTest binary on the DUT.

    Returns:
      a bool indicating if all tests in the binary passed
    """
    cmd = [path]
    logging.info('Running native test command: %s', ' '.join(cmd))
    output = self.dut.shell(cmd).decode('utf-8')
    logging.info('Got GTest output:\n%s', output)

    all_pass = True
    results = self._parse_gtest_result(output)
    logging.debug('Parsed GTest result: %s', results)
    for method, record in results.items():
      logging.info('Writing record for: %s', method)
      self.results.add_record(record)
      self.summary_writer.dump(
          record.to_dict(), records.TestSummaryEntryType.RECORD
      )
      if record.result != records.TestResultEnums.TEST_RESULT_PASS:
        all_pass = False

    return all_pass

  def _create_record(self, test_name: str) -> records.TestResultRecord:
    return records.TestResultRecord(
        t_name=test_name,
        t_class=self.TAG,
    )

  def _parse_gtest_result(
      self, output: str
  ) -> dict[str, records.TestResultRecord]:
    # pylint: disable=line-too-long
    """Parses the output of a GTest run.

    Sample format of output expected:
      Running main() from external/googletest/googletest/src/gtest_main.cc
      [==========] Running 5 tests from 1 test suite.
      [----------] Global test environment set-up.
      [----------] 5 tests from KmsAtomicTests/KmsAtomicTests
      [ RUN      ] KmsAtomicTests/KmsAtomicTests.RunSubTests/AtomicInvalidParams
      [       OK ] KmsAtomicTests/KmsAtomicTests.RunSubTests/AtomicInvalidParams (953 ms)
      [ RUN      ] KmsAtomicTests/KmsAtomicTests.RunSubTests/AtomicPlaneDamage
      [       OK ] KmsAtomicTests/KmsAtomicTests.RunSubTests/AtomicPlaneDamage (1684 ms)
      [ RUN      ] KmsAtomicTests/KmsAtomicTests.RunSubTests/TestOnly
      [       OK ] KmsAtomicTests/KmsAtomicTests.RunSubTests/TestOnly (3995 ms)
      [ RUN      ] KmsAtomicTests/KmsAtomicTests.RunSubTests/PlanePrimaryOverlayMutableZpos
      platform_testing/tests/display/igt/src/igt_test_helper.cpp:118: Skipped
      IGT-Version: IGT_VERSION-GIT (x86_64) (Linux: 6.12.58-android16-6-gda2da0badf05-ab14590243 x86_64)
      Using IGT_SRANDOM=1767815670 for randomisation
      Opened device: /dev/dri/card0
      Starting subtest: plane-primary-overlay-mutable-zpos
      No dynamic tests executed.
      Subtest plane-primary-overlay-mutable-zpos: SKIP (4.068s)

      [  SKIPPED ] KmsAtomicTests/KmsAtomicTests.RunSubTests/PlanePrimaryOverlayMutableZpos (4911 ms)
      [ RUN      ] KmsAtomicTests/KmsAtomicTests.RunSubTests/PlaneImmutableZpos
      [       OK ] KmsAtomicTests/KmsAtomicTests.RunSubTests/PlaneImmutableZpos (1883 ms)
      [----------] 5 tests from KmsAtomicTests/KmsAtomicTests (13428 ms total)

      [----------] Global test environment tear-down
      [==========] 5 tests from 1 test suite ran. (13428 ms total)
      [  PASSED  ] 4 tests.
      [  SKIPPED ] 1 test, listed below:
      [  SKIPPED ] KmsAtomicTests/KmsAtomicTests.RunSubTests/PlanePrimaryOverlayMutableZpos

    Args:
      output: The stdout from the GTest binary.

    Returns:
      A dictionary mapping test names to their result records.

    """
    # See: tools/tradefederation/core/test_framework/com/android/tradefed/testtype/GTestResultParser.java;l=229-242?
    # pylint: enable=line-too-long
    test_name_pattern = r'[\w./:;-]+'
    run_pattern = re.compile(rf'\[ RUN      \] ({test_name_pattern})')
    ok_pattern = re.compile(rf'\[       OK \] ({test_name_pattern}).*')
    failed_pattern = re.compile(rf'\[  FAILED  \] ({test_name_pattern}).*')
    skipped_pattern = re.compile(rf'\[  SKIPPED \] ({test_name_pattern}).*')

    running = False
    details = []
    test_results = {}
    for line in output.splitlines():
      match = run_pattern.match(line)
      if match:
        # New run block so clear details.
        details.clear()
        running = True
        continue

      if not running:
        continue

      match = ok_pattern.match(line)
      if match:
        test_name = match.group(1)
        tr_record = self._create_record(test_name)
        tr_record.test_pass(e=signals.TestPass(details='\n'.join(details)))
        test_results[test_name] = tr_record
        running = False
        continue

      match = failed_pattern.match(line)
      if match:
        test_name = match.group(1)
        tr_record = self._create_record(test_name)
        tr_record.test_fail(e=signals.TestFail(details='\n'.join(details)))
        test_results[test_name] = tr_record
        running = False
        continue

      match = skipped_pattern.match(line)
      if match:
        test_name = match.group(1)
        tr_record = self._create_record(test_name)
        tr_record.test_skip(e=signals.TestSkip(details='\n'.join(details)))
        test_results[test_name] = tr_record
        running = False
        continue

      details.append(line)

    return test_results


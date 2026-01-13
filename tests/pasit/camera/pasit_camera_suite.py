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

"""PASIT Camera Suite."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner
from pasit.camera import capture_from_external_camera
from pasit.camera import launch_with_external_camera
from pasit.camera import plug_in_external_camera
from pasit.camera import unplug_external_camera


class PasitCameraSuite(base_suite.BaseSuite):
  """PASIT Camera Suite."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(
        unplug_external_camera.UnplugExternalCameraTest,
    )
    self.add_test_class(
        plug_in_external_camera.PlugInExternalCameraTest,
    )
    self.add_test_class(
        launch_with_external_camera.LaunchWithExternalCameraTest,
    )
    self.add_test_class(
        capture_from_external_camera.CaptureFromExternalCameraTest,
    )


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()

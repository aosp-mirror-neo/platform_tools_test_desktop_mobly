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

"""A sample test that demonstrates external imports."""

# Modules installed via 'pip'
from mobly import base_test
from mobly import test_runner
from mobly.controllers import android_device
from mobly.controllers.android_device_lib.services import screen_recorder

# Bundled modules via soong.
from tradefed_arg_wrap import wrap_tradefed_args


class ExternalImportTest(base_test.BaseTestClass):
  """A sample test that demonstrates importing various types of modules."""

  def setup_class(self):
    self.dut = self.register_controller(android_device)[0]

    self.dut.load_snippet('mbs', android_device.MBS_PACKAGE)

    # Register screen recorder service.
    configs = screen_recorder.Configs()
    self.dut.services.register(
        'screen_recorder',
        screen_recorder.ScreenRecorder,
        configs=configs
    )

  def test_hello(self):
    self.dut.mbs.makeToast('Hello World!')

  def teardown_test(self):
    # TODO(b/477946913#comment3): This function requires building opencv-python
    # from source.
    # self.dut.services.create_output_excerpts_all(self.current_test_info)
    pass


@wrap_tradefed_args
def main():
  test_runner.main()

if __name__ == '__main__':
  main()

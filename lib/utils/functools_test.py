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

"""Unit tests for the functools module."""

import unittest

from lib.utils import functools


class FunctoolsTest(unittest.TestCase):
  """Test class for the functools module."""

  def test_simple_test_class_has_expected_test_methods(self):
    @functools.generate_tests
    class SimpleTestClass:
      """Class with a single method and functools decorators."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method(self, param):
        pass

    self.assertNotIn('test_method', dir(SimpleTestClass))
    self.assertIn('test_method_variant_1', dir(SimpleTestClass))
    self.assertIn('test_method_variant_2', dir(SimpleTestClass))

  def test_complex_test_class_has_expected_test_methods(self):
    @functools.generate_tests
    class ComplexTestClass:
      """Class with multiple methods and functools decorators."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method_single_param(self, param):
        pass

      @functools.with_variants(
          variant_a=(1, 2),
      )
      def non_test_method_multiple_params(self, param1, param2):
        pass

      def test_another_method(self):
        pass

      def non_test_another_method(self):
        pass

    self.assertNotIn('test_method_single_param', dir(ComplexTestClass))
    self.assertIn('test_method_single_param_variant_1', dir(ComplexTestClass))
    self.assertIn('test_method_single_param_variant_2', dir(ComplexTestClass))

    self.assertNotIn('non_test_method_multiple_params', dir(ComplexTestClass))
    self.assertIn(
        'non_test_method_multiple_params_variant_a', dir(ComplexTestClass)
    )

    self.assertIn('test_another_method', dir(ComplexTestClass))
    self.assertIn('non_test_another_method', dir(ComplexTestClass))

  def test_no_variant_test_class_has_expected_test_methods(self):
    @functools.generate_tests
    class NoVariantTestClass:
      """Class with a single method and missing with_variants decorator."""

      def test_method(self):
        pass

    self.assertIn('test_method', dir(NoVariantTestClass))

  def test_no_generate_tests_class_has_expected_test_methods(self):
    class NoGenerateTestsClass:
      """Class with multiple methods and missing generate_tests decorator."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method(self, param):
        pass

      def test_another_method(self):
        pass

      def non_test_method(self):
        pass

    self.assertIn('test_method', dir(NoGenerateTestsClass))
    self.assertIn('test_another_method', dir(NoGenerateTestsClass))
    self.assertIn('non_test_method', dir(NoGenerateTestsClass))
    self.assertNotIn('test_method_variant_1', dir(NoGenerateTestsClass))
    self.assertNotIn('test_method_variant_2', dir(NoGenerateTestsClass))

  def test_parameter_mismatch_test_class_has_expected_test_methods(self):
    @functools.generate_tests
    class ParamMismatchTestClass:
      """Class with functools decorators that have mismatched parameters."""

      @functools.with_variants(variant_1=(1,), variant_2=(4,))
      def test_method_no_params(self):
        pass

      @functools.with_variants(variant_1=(1,), variant_2=(4,))
      def test_method_too_many_params(self, param1, param2):
        pass

      @functools.with_variants(
          variant_1=(
              1,
              2,
          ),
          variant_2=(
              4,
              5,
          ),
      )
      def test_method_too_few_params(self, param):
        pass

      @functools.with_variants(
          variant_1=('abc', 'def'),
          variant_2=(
              'ghi',
              'jkl',
          ),
      )
      def test_method_type_mismatch(self, param1: int, param2: int):
        pass

    self.assertNotIn('test_method_no_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_no_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertIn(
        'test_method_no_params_variant_2', dir(ParamMismatchTestClass)
    )

    self.assertNotIn('test_method_too_many_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_too_many_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertIn(
        'test_method_too_many_params_variant_2', dir(ParamMismatchTestClass)
    )

    self.assertNotIn('test_method_too_few_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_too_few_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertIn(
        'test_method_too_few_params_variant_2', dir(ParamMismatchTestClass)
    )

    self.assertNotIn('test_method_type_mismatch', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_type_mismatch_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertIn(
        'test_method_type_mismatch_variant_2', dir(ParamMismatchTestClass)
    )


if __name__ == '__main__':
  unittest.main()

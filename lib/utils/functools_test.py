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
    """Test class with a single method and functools decorators.

    Verify that the original test method is replaced by the generated tests.
    Verify that the generated tests have the correct parameters and are
    callable.
    """

    expected_param_value: int

    @functools.generate_tests
    class SimpleTestClass:
      """Class with a single method and functools decorators."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method(slf, param):
        self.assertEqual(param, expected_param_value)

    self.assertNotIn('test_method', dir(SimpleTestClass))
    self.assertIn('test_method_variant_1', dir(SimpleTestClass))
    expected_param_value = 1
    SimpleTestClass().test_method_variant_1()
    self.assertIn('test_method_variant_2', dir(SimpleTestClass))
    expected_param_value = 4
    SimpleTestClass().test_method_variant_2()

  def test_complex_test_class_has_expected_test_methods(self):
    """Test class with multiple methods and functools decorators.

    Verify that the methods with functools decorators are replaced by the
    generated tests, and the methods without functools decorators are not
    replaced.
    Verify that the generated tests have the correct parameters and are
    callable.
    """

    expected_param_values: tuple[int, int] = ()

    @functools.generate_tests
    class ComplexTestClass:
      """Class with multiple methods and functools decorators."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method_single_param(slf, param):
        self.assertEqual(param, expected_param_values[0])

      @functools.with_variants(
          variant_a=(1, 2),
          variant_b=(3, 4),
      )
      def non_test_method_multiple_params(slf, param1, param2):
        self.assertEqual(param1, expected_param_values[0])
        self.assertEqual(param2, expected_param_values[1])

      def test_another_method(slf):
        pass

      def non_test_another_method(slf):
        pass

    self.assertNotIn('test_method_single_param', dir(ComplexTestClass))
    self.assertIn('test_method_single_param_variant_1', dir(ComplexTestClass))
    expected_param_values = (1,)
    ComplexTestClass().test_method_single_param_variant_1()
    self.assertIn('test_method_single_param_variant_2', dir(ComplexTestClass))
    expected_param_values = (4,)
    ComplexTestClass().test_method_single_param_variant_2()

    self.assertNotIn('non_test_method_multiple_params', dir(ComplexTestClass))
    self.assertIn(
        'non_test_method_multiple_params_variant_a', dir(ComplexTestClass)
    )
    expected_param_values = (1, 2)
    ComplexTestClass().non_test_method_multiple_params_variant_a()
    self.assertIn(
        'non_test_method_multiple_params_variant_b', dir(ComplexTestClass)
    )
    expected_param_values = (3, 4)
    ComplexTestClass().non_test_method_multiple_params_variant_b()

    self.assertIn('test_another_method', dir(ComplexTestClass))
    ComplexTestClass().test_another_method()

    self.assertIn('non_test_another_method', dir(ComplexTestClass))
    ComplexTestClass().non_test_another_method()

  def test_no_variant_test_class_has_expected_test_methods(self):
    """Test class with a single method and missing with_variants decorator.

    Verify that the original test method is not replaced.
    """

    @functools.generate_tests
    class NoVariantTestClass:
      """Class with a single method and missing with_variants decorator."""

      def test_method(slf):
        pass

    self.assertIn('test_method', dir(NoVariantTestClass))
    NoVariantTestClass().test_method()

  def test_no_generate_tests_class_has_expected_test_methods(self):
    """Test class with multiple methods and missing generate_tests decorator.

    Verify that the original test methods are not replaced.
    """

    class NoGenerateTestsClass:
      """Class with multiple methods and missing generate_tests decorator."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method(slf, param):
        pass

      def test_another_method(slf):
        pass

      def non_test_method(slf):
        pass

    self.assertIn('test_method', dir(NoGenerateTestsClass))
    self.assertRaisesRegex(
        TypeError,
        r"missing 1 required positional argument: 'param'",
        NoGenerateTestsClass().test_method,
    )
    self.assertIn('test_another_method', dir(NoGenerateTestsClass))
    NoGenerateTestsClass().test_another_method()
    self.assertIn('non_test_method', dir(NoGenerateTestsClass))
    NoGenerateTestsClass().non_test_method()
    self.assertNotIn('test_method_variant_1', dir(NoGenerateTestsClass))
    self.assertNotIn('test_method_variant_2', dir(NoGenerateTestsClass))

  def test_parameter_mismatch_test_class_has_expected_test_methods(self):
    """Test class with functools decorators that have mismatched parameters.

    Verify that the original test method without parameters is replaced but
    raises a TypeError when called.
    """

    @functools.generate_tests
    class ParamMismatchTestClass:
      """Class with functools decorators that have mismatched parameters."""

      @functools.with_variants(variant_1=(1,))
      def test_method_no_params(slf):
        pass

      @functools.with_variants(variant_1=(1,))
      def test_method_too_many_params(slf, param1, param2):
        pass

      @functools.with_variants(variant_1=(1, 2))
      def test_method_too_few_params(slf, param):
        pass

      @functools.with_variants(variant_1=('abc', 'def'))
      def test_method_type_mismatch(slf, param1: int, param2: int):
        self.assertEqual(param1, 'abc')
        self.assertEqual(param2, 'def')

    self.assertNotIn('test_method_no_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_no_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertRaisesRegex(
        TypeError,
        r'takes 1 positional argument but 2 were given',
        ParamMismatchTestClass().test_method_no_params_variant_1,
    )

    self.assertNotIn('test_method_too_many_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_too_many_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertRaisesRegex(
        TypeError,
        r"missing 1 required positional argument: 'param2'",
        ParamMismatchTestClass().test_method_too_many_params_variant_1,
    )

    self.assertNotIn('test_method_too_few_params', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_too_few_params_variant_1', dir(ParamMismatchTestClass)
    )
    self.assertRaisesRegex(
        TypeError,
        r'takes 2 positional arguments but 3 were given',
        ParamMismatchTestClass().test_method_too_few_params_variant_1,
    )

    self.assertNotIn('test_method_type_mismatch', dir(ParamMismatchTestClass))
    self.assertIn(
        'test_method_type_mismatch_variant_1', dir(ParamMismatchTestClass)
    )
    ParamMismatchTestClass().test_method_type_mismatch_variant_1()


if __name__ == '__main__':
  unittest.main()

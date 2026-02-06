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

  def test_no_method_decorator_with_class_decorator(self):
    """Test class with a single method and missing method decorators.

    Verify that the original test method is not replaced.
    """

    @functools.generate_tests
    class NoMethodDecoratorTestClass:
      """Class with a single method and missing method decorator."""

      def test_method(slf):  # pylint: disable=no-self-argument
        pass

    self.assertIn('test_method', dir(NoMethodDecoratorTestClass))
    NoMethodDecoratorTestClass().test_method()

  def test_no_generate_tests_class(self):
    """Test class with multiple methods and missing generate_tests decorator.

    Verify that the original test methods are not replaced.
    """

    class NoGenerateTestsClass:
      """Class with multiple methods and missing generate_tests decorator."""

      @functools.with_variants(
          variant_1=(1,),
          variant_2=(4,),
      )
      def test_method_variants(slf, param):  # pylint: disable=no-self-argument
        pass

      @functools.with_dimensions(variant_1=1, variant_2=2)
      @functools.with_dimensions(param_a='a', param_b='b')
      def test_method_matrix(slf, variant, param):  # pylint: disable=no-self-argument
        pass

      def test_another_method(slf):  # pylint: disable=no-self-argument
        pass

      def non_test_method(slf):  # pylint: disable=no-self-argument
        pass

    self.assertIn('test_method_variants', dir(NoGenerateTestsClass))
    self.assertRaisesRegex(
        TypeError,
        r"missing 1 required positional argument: 'param'",
        NoGenerateTestsClass().test_method_variants,
    )
    self.assertIn('test_method_matrix', dir(NoGenerateTestsClass))
    self.assertRaisesRegex(
        TypeError,
        r"missing 2 required positional arguments: 'variant' and 'param'",
        NoGenerateTestsClass().test_method_matrix,
    )
    self.assertIn('test_another_method', dir(NoGenerateTestsClass))
    NoGenerateTestsClass().test_another_method()
    self.assertIn('non_test_method', dir(NoGenerateTestsClass))
    NoGenerateTestsClass().non_test_method()

    self.assertNotIn(
        'test_method_variants_variant_1', dir(NoGenerateTestsClass)
    )
    self.assertNotIn(
        'test_method_variants_variant_2', dir(NoGenerateTestsClass)
    )
    self.assertNotIn(
        'test_method_matrix_variant_1_param_a', dir(NoGenerateTestsClass)
    )
    self.assertNotIn(
        'test_method_matrix_variant_1_param_b', dir(NoGenerateTestsClass)
    )
    self.assertNotIn(
        'test_method_matrix_variant_2_param_a', dir(NoGenerateTestsClass)
    )
    self.assertNotIn(
        'test_method_matrix_variant_2_param_b', dir(NoGenerateTestsClass)
    )


class WithVariantsTest(unittest.TestCase):
  """Test class for the with_variants decorator."""

  def test_simple_variants(self):
    """Test class with a single method and with_variants decorator.

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
      def test_method(slf, param):  # pylint: disable=no-self-argument
        self.assertEqual(param, expected_param_value)

    self.assertNotIn('test_method', dir(SimpleTestClass))
    self.assertIn('test_method_variant_1', dir(SimpleTestClass))
    expected_param_value = 1
    SimpleTestClass().test_method_variant_1()
    self.assertIn('test_method_variant_2', dir(SimpleTestClass))
    expected_param_value = 4
    SimpleTestClass().test_method_variant_2()

  def test_complex_variants(self):
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
      def test_method_single_param(slf, param):  # pylint: disable=no-self-argument
        self.assertEqual(param, expected_param_values[0])

      @functools.with_variants(
          variant_a=(1, 2),
          variant_b=(3, 4),
      )
      def non_test_method_multiple_params(slf, param1, param2):  # pylint: disable=no-self-argument
        self.assertEqual(param1, expected_param_values[0])
        self.assertEqual(param2, expected_param_values[1])

      def test_another_method(slf):  # pylint: disable=no-self-argument
        pass

      def non_test_another_method(slf):  # pylint: disable=no-self-argument
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

  def test_parameter_mismatch(self):
    """Test class with functools decorators that have mismatched parameters.

    Verify that the original test method without parameters is replaced but
    raises a TypeError when called.
    """

    @functools.generate_tests
    class ParamMismatchTestClass:
      """Class with functools decorators that have mismatched parameters."""

      @functools.with_variants(variant_1=(1,))
      def test_method_no_params(slf):  # pylint: disable=no-self-argument
        pass

      @functools.with_variants(variant_1=(1,))
      def test_method_too_many_params(slf, param1, param2):  # pylint: disable=no-self-argument
        pass

      @functools.with_variants(variant_1=(1, 2))
      def test_method_too_few_params(slf, param):  # pylint: disable=no-self-argument
        pass

      @functools.with_variants(variant_1=('abc', 'def'))
      def test_method_type_mismatch(slf, param1: int, param2: int):  # pylint: disable=no-self-argument
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


class WithDimensionsTest(unittest.TestCase):
  """Test class for the with_dimensions decorator."""

  def test_simple_dimensions(self):
    """Test class with a single method and with_dimensions decorator.

    Verify that the original test method is replaced by the generated tests.
    Verify that the generated tests have the correct parameters and are
    callable.
    """

    expected_param_value: str

    @functools.generate_tests
    class SimpleTestClass:
      """Class with a single method and with_dimensions decorator."""

      @functools.with_dimensions(param_a='a', param_b='b')
      def test_method(slf, param: str):  # pylint: disable=no-self-argument
        self.assertEqual(param, expected_param_value)

    self.assertNotIn('test_method', dir(SimpleTestClass))

    self.assertIn('test_method_param_a', dir(SimpleTestClass))
    expected_param_value = 'a'
    SimpleTestClass().test_method_param_a()

    self.assertIn('test_method_param_b', dir(SimpleTestClass))
    expected_param_value = 'b'
    SimpleTestClass().test_method_param_b()

  def test_complex_dimensions(self):
    """Test class with multiple with_dimensions decorators.

    Verify that the original test method is replaced by the generated tests.
    Verify that the generated tests have the correct parameters and are
    callable.
    """

    expected_num_displays: int
    expected_param_value: str

    @functools.generate_tests
    class ComplexTestClass:
      """Class with a single method and with_dimensions decorator."""

      @functools.with_dimensions(one_display=1, two_displays=2)
      @functools.with_dimensions(param_a='a', param_b='b')
      def test_method(slf, num_displays: int, param: str):  # pylint: disable=no-self-argument
        self.assertEqual(num_displays, expected_num_displays)
        self.assertEqual(param, expected_param_value)

    self.assertNotIn('test_method', dir(ComplexTestClass))

    self.assertIn('test_method_one_display_param_a', dir(ComplexTestClass))
    expected_num_displays = 1
    expected_param_value = 'a'
    ComplexTestClass().test_method_one_display_param_a()

    self.assertIn('test_method_one_display_param_b', dir(ComplexTestClass))
    expected_num_displays = 1
    expected_param_value = 'b'
    ComplexTestClass().test_method_one_display_param_b()

    self.assertIn('test_method_two_displays_param_a', dir(ComplexTestClass))
    expected_num_displays = 2
    expected_param_value = 'a'
    ComplexTestClass().test_method_two_displays_param_a()

    self.assertIn('test_method_two_displays_param_b', dir(ComplexTestClass))
    expected_num_displays = 2
    expected_param_value = 'b'
    ComplexTestClass().test_method_two_displays_param_b()


if __name__ == '__main__':
  unittest.main()

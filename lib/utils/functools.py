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

"""Decorators for creating variants of a test case

This module provides a decorators that minimize boilerplate code when creating
parameterized test cases for.
"""

import functools
import itertools


def with_variants(**kwargs):
  """Method decorator that attaches variant arguments to a test function.

  Usage:
      @with_variants(
          positive_case=(5, 10, 50),
          negative_case=(-4, -5, 20)
      )
      def test_multiplication(self, a, b, expected):
          # ... test logic ...

  Args:
      **kwargs: Each keyword argument represents a test variant. The key is used
        as a name suffix for the generated test. The value is a tuple or list of
        arguments for the test method.
  """

  def decorator(func):
    # Attach the variants to the function object itself for later processing.
    setattr(func, '_variants', kwargs)
    return func

  return decorator


def generate_tests(cls):
  """Class decorator to find methods marked with @_variants and generate

  actual test methods for the unittest runner to discover.
  """
  # Iterate over a copy of the class's attributes to allow modification.
  for name, obj in list(cls.__dict__.items()):
    if hasattr(obj, '_variants'):
      variants = getattr(obj, '_variants')

      # Remove the original template method from the class so the
      # test runner doesn't try to run it.
      delattr(cls, name)

      # Create and add a new test method for each variant.
      for variant_name, variant_args in variants.items():
        # Using a closure to create the test function ensures that the correct
        # variant arguments are used for each test.
        def create_test_function(original_func, args):
          @functools.wraps(original_func)
          def test_func(self):
            return original_func(self, *args)

          return test_func

        new_test_func = create_test_function(obj, variant_args)

        # Create a descriptive name for the new test method.
        new_test_name = f'{name}_{variant_name}'

        # Add the new test method to the class.
        setattr(cls, new_test_name, new_test_func)
  return cls


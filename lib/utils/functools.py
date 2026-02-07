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

"""Decorator for creating variants of a test case

This module provides a decorator that minimize boilerplate code when creating
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


def with_dimensions(**dim_kwargs):
  """Combines multiple dimensions into a single flat set of variants.

  Usage:
    @with_dimensions(on=PowerState.ON, off=PowerState.OFF),
    @with_dimensions(dock=ConnectionType.DOCK, dockless=ConnectionType.DOCKLESS)
    def test_something(self, power_state, connection_type):
      # ... test logic ...

  Translates to:
      @with_variants(
          on_dock=(PowerState.ON, ConnectionType.DOCK),
          on_dockless=(PowerState.ON, ConnectionType.DOCKLESS),
          off_dock=(PowerState.OFF, ConnectionType.DOCK),
          off_dockless=(PowerState.OFF, ConnectionType.DOCKLESS),
      )
      def test_something(self, power_state, connection_type):
          # ... test logic ...

  Args:
      **dim_kwargs: Each keyword argument represents a dimension. The key is
        used as a name prefix for the generated test. The value is a tuple or
        list of arguments for the test method.

  Returns:
      A decorator that combines the dimensions into a single set of variants.
  """

  def decorator(func):
    # Check if we are already building a matrix from a previous decorator.
    # We store the pending matrix in a hidden attribute on the function
    if not hasattr(func, '_pending_variants'):
      # Base case: start with one empty variant
      current_variants = {'': ()}
    else:
      current_variants = func._pending_variants  # pylint: disable=protected-access

    result_variants = {}
    for (suffix, args), (dim_key, dim_val) in itertools.product(
        current_variants.items(), dim_kwargs.items()
    ):
      # Build the suffix from the dimension name and the current suffix.
      # For example, the first time, it will be "on", but the
      # second time it will be "on_dock"
      # Note: decorators are applied bottom-up, so the first decorator will
      # be the last one applied.
      new_suffix = f'{dim_key}_{suffix}'.strip('_')

      # Ensure the dimension value is a tuple.
      val_as_tuple = dim_val if isinstance(dim_val, tuple) else (dim_val,)
      # Combine the current variants with the new dimension.
      result_variants[new_suffix] = val_as_tuple + args

    # Store the progress back on the function
    func._pending_variants = result_variants  # pylint: disable=protected-access

    # If this is the 'top' decorator, it calls with_variants.
    # However, to make stacking easy, we can wrap the final call.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      return func(*args, **kwargs)

    # Trigger the original with_variants only when
    # the framework actually looks for the method.
    return with_variants(**result_variants)(func)

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

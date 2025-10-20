# Desktop Mobly tests and test libraries

## tests/

Mobly tests go here. The tests are organized by project/team. Further
organization under project/team is up to the OWNERS of that folder.

### pasit/

Within pasit, the tests are organized by subsystem (camera, display, storage).
Additionaly, there are tests for pasit library that require a physical DUT
(under component/), and tests to validate the pasit testbed (under testbed/).

### Guidelines

-   Use `verify_` prefix for methods that contains asserts.
-   In pasit tests, define values for retry policy in test_policy.py

## lib/

Code that is not tests goes here (except unit tests). Organized by the
functionality it provides, and intended to be used by mobly/tests code.

### Guidelines

-   Do not include asserts or TestErrors in the library code. Raise an error or
    return appropriate value instead.

## tools/

Scripts or other types of tools that are not used by the tests directly.
Organized by the functionality they provide.

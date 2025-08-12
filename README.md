# Desktop Mobly tests and test libraries

## tests/

Mobly tests go here. The tests are organized by project/team. Further
organization under project/team is up to the OWNERS of that folder.

### Guidelines

-   Use `verify_` prefix for methods that contains asserts.
-   Define values for `delay_seconds` and `max_tries` for `retry` in local
    private constants.

## lib/

Code that is not tests goes here. Organized by the functionality it provides,
and intended to be used by mobly/tests code.

### Guidelines

-   Do not include asserts or TestErrors in the libraries. Raise an error or
    return appropriate value instead.

## tools/

Scripts or other types of tools that are not used by the tests directly.
Organized by the functionality they provide.

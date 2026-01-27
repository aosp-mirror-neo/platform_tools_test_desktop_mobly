# Mobly Sample Tests

This directory contains sample tests that demonstrate various features and best practices for writing Mobly tests in the Android Superproject.

## ExternalImportTest

Demonstrates how to use various types of dependencies including:
* External modules installed at runtime using pip.
* Other Soong Python modules included in the bundle.
* Other .apk modules built using Soong to be installed on the device.

### How to Run

This test requires using Tradefed to run via `atest`:

```
atest ExternalImportTest -- --module-arg ExternalImportTest:mobly-wildcard-config:false --module-arg ExternalImportTest:mobly-options:--config=<path_to_your_config>.yaml
```

If you see errors related to `pip` module installation, you may need to run
`gpkg setup python`.

There is Android specific implementation in this folder. It is assumed that
controller is an instance of android_device.AndroidDevice.

General guidelines:

1.  Snippet calls are RPCs and need to be wrapped in try-except for better
    debuggability.

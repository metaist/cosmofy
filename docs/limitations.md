# Limitations

Current constraints of cosmofy and Cosmopolitan Python.

## Pure Python Only

Currently, cosmofy can only bundle pure-Python packages. Packages with C extensions are not supported.

**Works:**

- Pure Python packages
- Packages using `ctypes` to load system libraries

**Does not work:**

- NumPy, Pandas, and other packages with compiled extensions
- Packages requiring Cython compilation

See [#94](https://github.com/metaist/cosmofy/issues/94) for progress on C extension support.

## Python Version

Bundles use the Cosmopolitan Python version from [cosmo.zip](https://cosmo.zip/pub/cosmos/bin/python), currently Python 3.12.

Custom Python versions are not currently supported. See [#44](https://github.com/metaist/cosmofy/issues/44).

## Bytecode Compilation

Automatic Python bytecode compilation (`.pyc` files) is currently disabled.

See [#41](https://github.com/metaist/cosmofy/issues/41).

## Platform-Specific Features

Some platform-specific features may behave differently:

- **File paths** - Cosmopolitan normalizes paths across platforms
- **Process spawning** - Some multiprocessing patterns may differ
- **Native libraries** - System library loading varies by platform

## Bundle Size

Bundles include a full Python interpreter, so minimum size is ~15-20MB.

Tips to reduce size:

- Only include necessary dependencies
- Use `--entry` to bundle specific entry points
- Consider using a `.args` file to share one Python bundle

## Self-Updater Security

The self-updater verifies binary hashes but does not cryptographically sign receipts. See [Self-Updater Security](self-updater.md#security-considerations).

Receipt signing is planned for a future release ([#53](https://github.com/metaist/cosmofy/issues/53)).

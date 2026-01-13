# .args File

Cosmopolitan Python bundles have a special `.args` file that configures how Python starts.

## What is .args?

When a Cosmopolitan Python bundle runs, it reads `.args` to determine:

- Which module to run (`-m module_name`)
- Command-line arguments to Python
- Script to execute

The `.args` file is embedded inside the bundle and is set during `cosmofy bundle`.

## Viewing .args

```bash
uvx cosmofy fs args my_bundle
# Output: -m my_module
```

## Setting .args

```bash
uvx cosmofy fs args my_bundle '-m other_module'
```

## Self-Updater and .args

When using the [self-updater](self-updater.md), the bundle first checks for `--self-update` before processing `.args`.

If `--self-update` is NOT present, the bundle processes `.args` normally. However, since Python has already started, only certain CLI options are supported.

## Supported Python Options

The following [Python command-line options](https://docs.python.org/3/using/cmdline.html) are supported:

| Option | Description |
|--------|-------------|
| `-c <command>` | Run a command |
| `-m <module>` | Run a module (most common) |
| `-` | Read command from stdin |
| `<script>` | Run a script on the filesystem |
| `-V`, `--version` | Display Python version (`-VV` also supported) |
| `-h`, `-?`, `--help` | Show help message |
| `-i` | Enter REPL after executing script |
| `-q` | Quiet mode (no copyright/version in REPL) |

If no option is provided, the Python REPL runs.

## Examples

### Run a Module

```bash
uvx cosmofy fs args my_bundle '-m my_package.cli'
```

### Run a Script

```bash
uvx cosmofy fs args my_bundle 'Lib/site-packages/my_script.py'
```

### Enter REPL

```bash
uvx cosmofy fs args my_bundle ''  # empty = REPL
```

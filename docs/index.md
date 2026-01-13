# cosmofy: Cosmopolitan Python Bundler

**One binary. Every platform.**

`cosmofy` bundles your Python app into a **single executable** that runs on Linux, macOS, and Windows using [Cosmopolitan libc](https://github.com/jart/cosmopolitan).

## Quick Start

```bash
uv tool install cosmofy  # or: pip install cosmofy
uvx cosmofy bundle       # produces dist/my_command
```

## Why cosmofy?

- **Single binary distribution** - No Python installation required on target machines
- **Cross-platform** - Same binary runs on Linux, macOS, and Windows
- **Simple** - Works with your existing `pyproject.toml`
- **Self-updating** - Optional built-in update mechanism

## How It Works

1. **Bundle** - `cosmofy bundle` packages your Python app with Cosmopolitan Python
2. **Distribute** - Share a single file that works everywhere
3. **Update** - Optional self-updater keeps binaries current

## Documentation

- [Getting Started](getting-started.md) - Installation and first bundle
- [Bundling](bundling.md) - How bundling works
- [Self-Updater](self-updater.md) - Automatic updates (experimental)
- [.args File](args-file.md) - Cosmopolitan Python configuration
- [Filesystem Commands](fs-commands.md) - Inspect and modify bundles
- [CLI Reference](cli.md) - All commands
- [Limitations](limitations.md) - Current constraints

## Links

- [GitHub Repository](https://github.com/metaist/cosmofy)
- [PyPI Package](https://pypi.org/project/cosmofy)
- [Changelog](https://github.com/metaist/cosmofy/blob/main/CHANGELOG.md)


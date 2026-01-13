# cosmofy: Cosmopolitan Python Bundler

<p align="center">
  <a href="https://github.com/metaist/cosmofy/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/cosmofy/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="PyPI" src="https://img.shields.io/pypi/v/cosmofy.svg?color=blue" /></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/cosmofy" /></a>
</p>

`cosmofy` bundles your Python app using [`uv`](https://docs.astral.sh/uv/) into a **single executable** which runs on Linux, macOS, and Windows using [Cosmopolitan libc](https://github.com/jart/cosmopolitan).

## Install

```bash
uv tool install cosmofy  # recommended
# or
pip install cosmofy      # classic
```

Or download the [portable binary](https://github.com/metaist/cosmofy/releases/latest/download/cosmofy).

## Quick Example

Define your entry point in `pyproject.toml`:

```toml
[project.scripts]
my_command = "my_command.__main__:main"
```

Bundle your project:

```bash
uvx cosmofy bundle  # produces dist/my_command
```

Or bundle a script:

```bash
uv init --script myscript.py
uvx cosmofy bundle --script myscript.py  # produces dist/myscript
```

## Limitations

- Pure-Python only (no C extensions) - see [#94](https://github.com/metaist/cosmofy/issues/94)
- Tied to latest Cosmopolitan Python version - see [#44](https://github.com/metaist/cosmofy/issues/44)

## Documentation

- [Getting Started](https://docs.metaist.com/cosmofy/getting-started/)
- [Bundling](https://docs.metaist.com/cosmofy/bundling/)
- [Self-Updater](https://docs.metaist.com/cosmofy/self-updater/)
- [.args File](https://docs.metaist.com/cosmofy/args-file/)
- [Filesystem Commands](https://docs.metaist.com/cosmofy/fs-commands/)
- [CLI Reference](https://docs.metaist.com/cosmofy/cli/)

**[Read the full documentation](https://docs.metaist.com/cosmofy/)**

## License

[MIT License](https://github.com/metaist/cosmofy/blob/main/LICENSE.md)

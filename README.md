# cosmofy: Cosmopolitan Python Bundler

<p align="center">
  <a href="https://github.com/metaist/cosmofy/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/cosmofy/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="PyPI" src="https://img.shields.io/pypi/v/cosmofy.svg?color=blue" /></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/cosmofy" /></a>
</p>

`cosmofy` bundles your python app into a **single executable** which runs on Linux, macOS, and Windows. It uses [Cosmopolitan libc](https://github.com/jart/cosmopolitan).

## Install

macOS / Linux:

```bash
dest=~/.local/bin/cosmofy
curl -sSz $dest -o $dest -L https://github.com/metaist/cosmofy/releases/latest/download/cosmofy
chmod +x $dest
```

Windows: (PowerShell instructions coming soon)

## Examples

```bash
# bundle a single script
cosmofy examples/single-file/file-with-main.py

# bundle a directory
cosmofy examples/pkg-nested

# add additional args, change output path
cosmofy src/cosmofy --args '-m cosmofy --cosmo' --output dist/cosmofy

# add self-updater
cosmofy src/cosmofy \
  --args '-m cosmofy --cosmo' \
  --release-url https://github.com/metaist/cosmofy/releases/latest/download/cosmofy
```

## Usage

<!--[[[cog
from cosmofy.args import USAGE
cog.outl(f"\n```text\n{USAGE}```\n")
]]]-->

```text
cosmofy: Cosmopolitan Python Bundler

USAGE

  cosmofy
    [--help] [--version] [--debug] [--dry-run] [--self-update]
    [--python-url URL] [--cache PATH] [--clone]
    [--output PATH] [--args STRING]
    <add>... [--exclude GLOB]... [--remove GLOB]...
    [--receipt PATH] [--receipt-url URL] [--release-url URL]
    [--release-version STRING]

GENERAL

  -h, --help        Show this help message and exit.
  --version         Show program version and exit.
  --debug           Show debug messages.
  -n, --dry-run     Do not make any file system changes.
  --self-update     Update `cosmofy` to the latest version.

CACHE

  --python-url URL
    URL from which to download Cosmopolitan Python.
    [default: https://cosmo.zip/pub/cosmos/bin/python]
    [env: COSMOFY_PYTHON_URL=]

  --cache PATH
    Directory in which to cache Cosmopolitan Python downloads.
    Use `false` or `0` to disable caching.
    [default: ~/.cache/cosmofy]
    [env: COSMOFY_CACHE_DIR=]

  --clone
    Obtain python by cloning `cosmofy` and removing itself instead of
    downloading it from `--python-url`.

OUTPUT

  -o PATH, --output PATH
    Path to output file.
    [default: `<main_module>.com`]

    `<main_module>` is the first module with a `__main__.py` or file with an
    `if __name__ == "__main__"` line.

FILES

  --args STRING
    Cosmopolitan Python arguments.
    [default: `"-m <main_module>"`]

  --add GLOB, <add>
    At least one glob-like patterns to add. Folders are recursively added.
    Files ending in `.py` will be compiled.

  -x GLOB, --exclude GLOB
    One or more glob-like patterns to exclude from being added.

    Common things to exclude are egg files and python cache:
    $ cosmofy src -x "**/*.egg-info/*" -x "**/__pycache__/*"

  --rm GLOB, --remove GLOB
    One or more glob-like patters to remove from the output.

    Common things to remove are `pip`, terminal info, and SSL certs:
    $ cosmofy src/my_module --rm 'usr/*' --rm 'Lib/site-packages/pip/*'

SELF-UPDATER

  Specifying any of the options below will add `cosmofy.updater`
  to make the resulting app capable of updating itself. You
  must supply at least `--receipt-url` or `--release-url`.

  In addition to building the app, there will be a second output
  which is a JSON file (called a receipt) that needs to be uploaded
  together with the app.

  When the app runs, the updater first checks to see if it was called with
  `--self-update`. If it wasn't, execution continues as normal.
  If it was, the updater checks the published receipt to see if there is a
  newer version of the app and downloads it, if appropriate.

  NOTE: The updater will alter `--args` so that it gets called first.
  It supports most Python Command Line interface options (like `-m`).
  For a full list see: https://github.com/metaist/cosmofy#supported-python-cli

  --receipt PATH
    Set the path for the JSON receipt.
    [default: `<output>.json`]

  --receipt-url URL
    URL to the published receipt.
    [default: --release-url + .json]
    [env: RECEIPT_URL=]

  --release-url URL
    URL to the file to download.
    [default: --receipt-url without .json]
    [env: RELEASE_URL=]

  --release-version STRING
    Release version.
    [default: first version-like string in `$(${output} --version)`]
```

<!--[[[end]]]-->

## Self Updater

If you provide `--receipt-url` or `--release-url`, `cosmofy` will add a self-updater
to the output bundle. This self-updater will look for the `--self-update` option on the command line and look for an updated release. When the option is absent, it will run `--args` as usual (see below for minor limitations).

## Supported Python CLI

Cosmopolitan Python apps have a special `.args` file which is read when it starts up. The contents of this file are typically set by the `--args` option. However,
when using the [self-updater](#self-updater), we need to check for the
`--self-update` option first. If it is absent we process the rest of the `--args`
as usual. However, since Python has already started running we only support the
following [Python Command Line Interface options](https://docs.python.org/3/using/cmdline.html):

- `-c <command>`: run a command
- `-m <module-name>`: run a module (this is the most common)
- `-`: read a command from `stdin` (rare, but we support it)
- `<script>`: run a script on the filesystem
- `-V, --version`: display the Python version (we also support `-VV`)
- `-h, -?, --help`: show relevant portions of the help message
- `-i`: enter python REPL after executing a script (`-c`, `-m`, `-`, or `<script>`)
- `-q`: don't display copyright and version messages in interactive mode

If no option is provided, the Python REPL will run.

## License

[MIT License](https://github.com/metaist/cosmofy/blob/main/LICENSE.md)

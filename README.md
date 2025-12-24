# cosmofy: Cosmopolitan Python Bundler

<p align="center">
  <a href="https://github.com/metaist/cosmofy/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/cosmofy/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="PyPI" src="https://img.shields.io/pypi/v/cosmofy.svg?color=blue" /></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/cosmofy" /></a>
</p>

`cosmofy` bundles your python app using [`uv`](https://docs.astral.sh/uv/) into a **single executable** which runs on
Linux, macOS, and Windows using [Cosmopolitan libc](https://github.com/jart/cosmopolitan).

## Install

First, make sure you have [`uv` installed](https://docs.astral.sh/uv/getting-started/installation/).

To use the latest version of `cosmofy` without installing, use `uvx`:

```bash
uvx cosmofy bundle
```

To install `cosmofy` locally:

```bash
uv tool install cosmofy # recommended
# or
pip install cosmofy # classic
```

You can also install the `cosmofy` binary directly.

macOS / Linux:

```bash
dest=~/.local/bin/cosmofy
curl -sSz $dest -o $dest -L https://github.com/metaist/cosmofy/releases/latest/download/cosmofy
chmod +x $dest
```

Windows:

```powershell
$dest = "$env:LOCALAPPDATA\cosmofy\cosmofy.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $dest)
Invoke-WebRequest -Uri "https://github.com/metaist/cosmofy/releases/latest/download/cosmofy" -OutFile $dest
```

## Examples

To bundle a project, first make sure you define `[project.scripts]` in your `pyproject.toml`:

```toml
[project.scripts]
my_command = "my_command.__main__:main"
```

The bundle the whole project:

```bash
uvx cosmofy bundle # produces `dist/my_command`
```

You can also bundle individual python files:

```bash
uv init --script myscript.py # or uv add --script myscript.py <some dependency>
uvx cosmofy bundle --script myscript.py # produces `dist/myscript`
```

## Limitations

- Currently, we can only bundle pure-Python code (no C extensions) (see [#94])
- Currently, we're tied to the latest Cosmopolitan Python version (see [#44]).
- Automatically compiling Python bytecode is currently disabled (see [#41]).

[#44]: https://github.com/metaist/cosmofy/issues/44
[#41]: https://github.com/metaist/cosmofy/issues/41
[#94]: https://github.com/metaist/cosmofy/issues/94

## Self Updater

> [!WARNING]
> This is an experimental feature. See [Security Considerations](#security-considerations).

There is experimental support for [adding a self-updater](#cosmofy-updater-add) to a cosmofy bundle:

```bash
uvx cosmofy updater add dist/my_cmd # produces dist/mc_cmd.json
```

This produces a `.json` receipt that you should publish together with your bundle.

- If the bundle is run with `--self-update` anywhere in the arguments,
  the cosmofy updater will run. It will compare it's internal build
  date with the date at `--receipt-url` and will download any updates, if
  they exist.

- Otherwise, the bundle will run as normal by calling `.args`.
  [See below](#supported-python-cli) for minor limitations.

## Security Considerations

The self-updater verifies downloaded binaries against the hash in the receipt,
but does not cryptographically verify the receipt itself. If you control the
receipt hosting, this provides integrity verification. For higher-assurance
scenarios, receipt signing is planned for a future release (see [#53]).

[#53]: https://github.com/metaist/cosmofy/issues/53

## Supported Python CLI

Cosmopolitan Python apps have a special `.args` file which is read when it
starts up. The contents of this file are typically set during
[`cosmofy bundle`](#cosmofy-bundle) and can be adjusted with
[`cosmofy fs args`](#cosmofy-fs-args).
However, when using the [self-updater](#self-updater), we need to check for
the `--self-update` option first.

If `--self-update` is NOT present, we want to process the rest of the
`.args` as usual. However, since Python has already started, we only support
the following [Python Command Line Interface options](https://docs.python.org/3/using/cmdline.html):

- `-c <command>`: run a command
- `-m <module-name>`: run a module (this is the most common)
- `-`: read a command from `stdin` (rare, but we support it)
- `<script>`: run a script on the filesystem
- `-V, --version`: display the Python version (we also support `-VV`)
- `-h, -?, --help`: show relevant portions of the help message
- `-i`: enter python REPL after executing a script (`-c`, `-m`, `-`, or `<script>`)
- `-q`: don't display copyright and version messages in interactive mode

If no option is provided, the Python REPL will run.

## Commands

- [`cosmofy bundle`](#cosmofy-bundle)
- [`cosmofy updater`](#cosmofy-updater)
  - [`cosmofy updater add`](#cosmofy-updater-add)
  - [`cosmofy updater remove`](#cosmofy-updater-remove)
  - [`cosmofy updater check`](#cosmofy-updater-check)
- [`cosmofy fs`](#cosmofy-fs)
  - [`cosmofy fs ls`](#cosmofy-fs-ls)
  - [`cosmofy fs cat`](#cosmofy-fs-cat)
  - [`cosmofy fs add`](#cosmofy-fs-add)
  - [`cosmofy fs rm`](#cosmofy-fs-rm)
  - [`cosmofy fs args`](#cosmofy-fs-args)
- [`cosmofy self`](#cosmofy-self)
  - [`cosmofy self update`](#cosmofy-self-update)
  - [`cosmofy self version`](#cosmofy-self-version)

### `cosmofy`

<!--[[[cog
from cosmofy.__main__ import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
A Cosmopolitan Python bundler.

Usage: cosmofy [OPTIONS] <COMMAND>

Commands:
  bundle                    build and bundle a project
  updater                   install/uninstall bundle self-updater
  fs                        inspect and modify an existing bundle
  self                      manage the `cosmofy` executable

Options:
      --version             display the program version and exit

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy bundle`

<!--[[[cog
from cosmofy.bundle import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Build a Python project into a Cosmopolitan bundle.

Usage: cosmofy bundle [OPTIONS]

Input options:
      --entry <NAME>        `console_script` entry points to bundle
      --script <PATH>       paths to bundle

      If neither --entry nor --script is specified, all entry points
      will be bundled. If both are specified, entries will be bundled first.

      --python-url <URL>    URL from which to download Cosmopolitan Python
                            [default: https://cosmo.zip/pub/cosmos/bin/python]
                            [env: COSMOFY_PYTHON_URL=]

Output options:
  -o, --output-dir <PATH>   output directory
                            [default: project-root/dist]

Cache options:
  -n, --no-cache            do not read or save to the cache
                            [env: COSMOFY_NO_CACHE=]
      --cache-dir <PATH>    store Cosmopolitan Python downloads
                            [default: ~/.cache/cosmofy]
                            [env: COSMOFY_CACHE_DIR=]

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy updater`

<!--[[[cog
from cosmofy.updater.__main__ import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
EXPERIMENTAL: Manage a bundle's self-updater.

Usage: cosmofy updater [OPTIONS] <COMMAND>

Commands:
  add                       add self-updater to a bundle
  remove                    remove self-updater from a bundle
  check                     check if the bundle has updates

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy updater add`

<!--[[[cog
from cosmofy.updater.add import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
EXPERIMENTAL: Add self-updater to a cosmofy bundle.

Usage: cosmofy updater add <BUNDLE> [OPTIONS]

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle

Receipt options:
      --receipt <PATH>      output path to the JSON receipt
                            default is <BUNDLE> + `.json`
      --receipt-url <URL>   URL to the published receipt
                            default is --release-url + `.json`
                            [env: RECEIPT_URL=]
      --release-url <URL>   URL to the file to download
                            default is --receipt-url without `.json`
                            [env: RELEASE_URL=]
      --release-version <STRING>
                            release version
                            default is $(<BUNDLE> --version)

Process options:
      --no-copy             skip copying `cosmofy` code
                            (e.g., its already a dependency)
                            [env: COSMOFY_NO_COPY=]
      --no-args             skip setting `.args`
                            [env: COSMOFY_NO_ARGS=]

read more: https://github.com/metaist/cosmofy#self-updater

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy updater remove`

<!--[[[cog
from cosmofy.updater.remove import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
EXPERIMENTAL: Remove cosmofy self-updater from a cosmofy bundle.

Usage: cosmofy updater remove <BUNDLE> [OPTIONS]

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle

Process options:
      --no-args             skip setting `.args`
                            [env: COSMOFY_NO_ARGS=]

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy updater check`

<!--[[[cog
from cosmofy.updater.check import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
EXPERIMENTAL: Check if a cosmofy bundle has an update.

Usage: cosmofy updater check <BUNDLE> [OPTIONS]

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle

Options:
      --receipt-url <URL>   override the published receipt URL
                            [env: RECEIPT_URL=]

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs`

<!--[[[cog
from cosmofy.fs.__main__ import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Cosmopolitan file system tool.

Usage: cosmofy fs [OPTIONS] <COMMAND>

Commands:
  ls                        list files in bundle
  cat                       print file contents
  add                       add files to bundle
  rm                        remove files from bundle
  args                      get/set special `.args` file in bundle

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs ls`

<!--[[[cog
from cosmofy.fs.ls import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
List contents of a Cosmopolitan bundle.

Usage: cosmofy fs ls <BUNDLE> [OPTIONS] [FILE]...

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle
  [FILE]...                 one or more file patterns to show

Filter options:
  -a, --all                 show entries whose name starts with `.`
  -B, --ignore-backups      hide entries whose name ends with `~`
      --hide <PATTERN>      hide matching entries, unless --all
  -I, --ignore <PATTERN>    hide matching entries, even with --all

Sort options:
  -r, --reverse             reverse the sort order
      --sort <MODE>         [choices: none, name, size, time, extension]
                            [default: name]

Output options:
  -l, --long                show permissions, size, and modified date
  -h, --human-readable      show sizes using powers of 1024 like 1K 2M 3G etc.
      --si                  show sizes using powers of 1000 (implies -h)

Global options:
      --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs cat`

<!--[[[cog
from cosmofy.fs.cat import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Print contents of a file within a Cosmopolitan bundle.

Usage: cosmofy fs cat <BUNDLE> <FILE>... [OPTIONS]

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle
  <FILE>...                 one or more file patterns to show

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs cat bundle.zip -- -weird-filename.txt

Options:
  -p, --prompt              prompt for a decryption password

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs add`

<!--[[[cog
from cosmofy.fs.add import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Add files to a Cosmopolitan bundle.

Usage: cosmofy fs add <BUNDLE> [OPTIONS] <FILE>...

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle
  <FILE>...                 files relative to current directory to add

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs add bundle.zip -- -weird-filename.txt

Options:
  -f, --force               overwrite existing files
      --chdir <PATH>        change to this directory before adding
      --dest                prefix to add in the bundle
                            Most python packages go into `Lib/site-packages`

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs rm`

<!--[[[cog
from cosmofy.fs.rm import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Remove files from a Cosmopolitan bundle.

Usage: cosmofy fs rm <BUNDLE> [OPTIONS] <FILE>...

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle
  <FILE>...                 files to remove

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs rm bundle.zip -- -weird-filename.txt

Options:
  -f, --force               ignore nonexistent files
  -r, --recursive           recursively remove directories

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy fs args`

<!--[[[cog
from cosmofy.fs.args import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Get or set the special `.args` files in a Cosmopolitan bundle.

These are the arguments to the Cosmopolitan Python.

Usage: cosmofy fs args <BUNDLE> [OPTIONS] [VAL]

Arguments:
  <BUNDLE>                  Cosmopolitan file bundle
  [VAL]                     value to set (if omitted, current value is printed)

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy self`

<!--[[[cog
from cosmofy.self.__main__ import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Manage the `cosmofy` executable.

Usage: cosmofy self [OPTIONS] <COMMAND>

Commands:
  update                    update `cosmofy`
  version                   display `cosmofy`'s version

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy self update`

<!--[[[cog
from cosmofy.self.update import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Update `cosmofy`.

Usage: cosmofy self update [OPTIONS]

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

### `cosmofy self version`

<!--[[[cog
from cosmofy.self.version import usage
cog.outl(f"\n```text\n{usage}```\n")
]]]-->

```text
Display `cosmofy`'s version.

Usage: cosmofy self version [OPTIONS]

Options:
      --short               only print the version
      --output-format NAME  [default: text][choices: text, json]

Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
```

<!--[[[end]]]-->

## License

[MIT License](https://github.com/metaist/cosmofy/blob/main/LICENSE.md)

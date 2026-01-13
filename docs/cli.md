# CLI Reference

<!--[[[cog
from cosmofy.__main__ import usage as main_usage
from cosmofy.bundle import usage as bundle_usage
from cosmofy.updater.__main__ import usage as updater_usage
from cosmofy.updater.add import usage as updater_add_usage
from cosmofy.updater.remove import usage as updater_remove_usage
from cosmofy.updater.check import usage as updater_check_usage
from cosmofy.fs.__main__ import usage as fs_usage
from cosmofy.fs.ls import usage as fs_ls_usage
from cosmofy.fs.cat import usage as fs_cat_usage
from cosmofy.fs.add import usage as fs_add_usage
from cosmofy.fs.rm import usage as fs_rm_usage
from cosmofy.fs.args import usage as fs_args_usage
from cosmofy.self.__main__ import usage as self_usage
from cosmofy.self.update import usage as self_update_usage
from cosmofy.self.version import usage as self_version_usage
]]]-->
<!--[[[end]]]-->

## cosmofy

<!--[[[cog cog.outl(f"\n```text\n{main_usage}```\n") ]]]-->

```text
A Cosmopolitan Python bundler.

Usage: cosmofy [OPTIONS] <COMMAND>

Commands:
  bundle                    build and bundle a project
  updater                   install/uninstall bundle self-updater
  fs                        inspect and modify an existing bundle
  self                      manage the `cosmofy` executable
  completions               generate shell completions

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

## cosmofy bundle

<!--[[[cog cog.outl(f"\n```text\n{bundle_usage}```\n") ]]]-->

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
  -s, --suffix <SUFFIX>     file extension for output executables
                            [default: '.com' on Windows, '' otherwise]
  -c, --compile-bytecode    compile .py files to .pyc using Cosmopolitan Python

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

## cosmofy updater

<!--[[[cog cog.outl(f"\n```text\n{updater_usage}```\n") ]]]-->

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

### cosmofy updater add

<!--[[[cog cog.outl(f"\n```text\n{updater_add_usage}```\n") ]]]-->

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

### cosmofy updater remove

<!--[[[cog cog.outl(f"\n```text\n{updater_remove_usage}```\n") ]]]-->

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

### cosmofy updater check

<!--[[[cog cog.outl(f"\n```text\n{updater_check_usage}```\n") ]]]-->

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

## cosmofy fs

<!--[[[cog cog.outl(f"\n```text\n{fs_usage}```\n") ]]]-->

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

### cosmofy fs ls

<!--[[[cog cog.outl(f"\n```text\n{fs_ls_usage}```\n") ]]]-->

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

### cosmofy fs cat

<!--[[[cog cog.outl(f"\n```text\n{fs_cat_usage}```\n") ]]]-->

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

### cosmofy fs add

<!--[[[cog cog.outl(f"\n```text\n{fs_add_usage}```\n") ]]]-->

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
  -c, --compile-bytecode    compile .py files to .pyc using the bundle's Python

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

### cosmofy fs rm

<!--[[[cog cog.outl(f"\n```text\n{fs_rm_usage}```\n") ]]]-->

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

### cosmofy fs args

<!--[[[cog cog.outl(f"\n```text\n{fs_args_usage}```\n") ]]]-->

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

## cosmofy self

<!--[[[cog cog.outl(f"\n```text\n{self_usage}```\n") ]]]-->

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

### cosmofy self update

<!--[[[cog cog.outl(f"\n```text\n{self_update_usage}```\n") ]]]-->

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

### cosmofy self version

<!--[[[cog cog.outl(f"\n```text\n{self_version_usage}```\n") ]]]-->

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

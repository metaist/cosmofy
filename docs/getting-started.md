# Getting Started

## Install

First, make sure you have [`uv` installed](https://docs.astral.sh/uv/getting-started/installation/).

### Using uvx (recommended)

Use the latest version without installing:

```bash
uvx cosmofy bundle
```

### Using uv tool

Install globally:

```bash
uv tool install cosmofy
```

### Using pip

```bash
pip install cosmofy
```

### Direct Binary Download

You can also download the `cosmofy` binary directly.

**macOS / Linux:**

```bash
dest=~/.local/bin/cosmofy
curl -sSz $dest -o $dest -L https://github.com/metaist/cosmofy/releases/latest/download/cosmofy
chmod +x $dest
```

**Windows:**

```powershell
$dest = "$env:LOCALAPPDATA\cosmofy\cosmofy.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $dest)
Invoke-WebRequest -Uri "https://github.com/metaist/cosmofy/releases/latest/download/cosmofy" -OutFile $dest
```

## Quick Example

### Bundling a Project

First, define your entry point in `pyproject.toml`:

```toml
[project.scripts]
my_command = "my_command.__main__:main"
```

Then bundle:

```bash
uvx cosmofy bundle  # produces dist/my_command
```

### Bundling a Script

You can also bundle individual Python files:

```bash
uv init --script myscript.py  # or: uv add --script myscript.py <dependency>
uvx cosmofy bundle --script myscript.py  # produces dist/myscript
```

## Next Steps

- [Bundling](bundling.md) - Learn more about bundling options
- [Self-Updater](self-updater.md) - Add automatic updates to your bundle
- [CLI Reference](cli.md) - See all available commands

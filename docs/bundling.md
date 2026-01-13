# Bundling

`cosmofy bundle` creates a Cosmopolitan Python bundle from your project.

## How It Works

1. **Downloads Cosmopolitan Python** - A universal Python binary from [cosmo.zip](https://cosmo.zip/pub/cosmos/bin/python)
2. **Installs Dependencies** - Uses `uv` to collect your project's dependencies
3. **Creates Bundle** - Packages everything into a single executable

## Entry Points

### From pyproject.toml

By default, `cosmofy bundle` bundles all entry points defined in `[project.scripts]`:

```toml
[project.scripts]
my_command = "my_command.__main__:main"
other_cmd = "my_package.cli:run"
```

```bash
uvx cosmofy bundle  # bundles both my_command and other_cmd
```

### Specific Entry Points

Bundle only specific entry points:

```bash
uvx cosmofy bundle --entry my_command
```

### Standalone Scripts

Bundle a single Python script:

```bash
uvx cosmofy bundle --script myscript.py
```

!!! note
    Scripts must have inline dependencies defined using `uv init --script` or `uv add --script`.

## Output

By default, bundles are placed in `dist/`:

```bash
uvx cosmofy bundle                    # -> dist/my_command
uvx cosmofy bundle -o build/          # -> build/my_command
```

## Caching

Cosmopolitan Python is cached to avoid repeated downloads:

```bash
# Default cache location
~/.cache/cosmofy/

# Custom cache location
uvx cosmofy bundle --cache-dir /tmp/cosmofy-cache

# Disable cache
uvx cosmofy bundle --no-cache
```

Environment variables:

- `COSMOFY_CACHE_DIR` - Custom cache directory
- `COSMOFY_NO_CACHE` - Disable caching

## Custom Python URL

Override the Cosmopolitan Python download URL:

```bash
uvx cosmofy bundle --python-url https://example.com/custom-python
```

Or set `COSMOFY_PYTHON_URL` environment variable.

## Bytecode Compilation

Compile Python files to bytecode (`.pyc`) for faster startup:

```bash
uvx cosmofy bundle --compile-bytecode
```

This uses the Cosmopolitan Python in the bundle to compile `.py` files. The trade-off is slightly larger bundle size for faster initial import times.

## Output Format

Get structured JSON output instead of text:

```bash
uvx cosmofy bundle --output-format json
```

The JSON output includes paths to all generated bundles:

```json
{
  "entry_points": ["dist/my_command"],
  "scripts": []
}
```

This is useful for scripting and CI/CD pipelines.

## Dry Run

See what would happen without making changes:

```bash
uvx cosmofy bundle --dry-run
```

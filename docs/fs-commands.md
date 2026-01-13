# Filesystem Commands

The `cosmofy fs` commands let you inspect and modify Cosmopolitan bundles.

Cosmopolitan bundles are ZIP files with an executable header. These commands manipulate the ZIP contents.

## List Files

```bash
uvx cosmofy fs ls my_bundle
```

### Options

```bash
# Show hidden files (starting with .)
uvx cosmofy fs ls my_bundle -a
uvx cosmofy fs ls my_bundle --all

# Hide backup files (ending with ~)
uvx cosmofy fs ls my_bundle -B
uvx cosmofy fs ls my_bundle --ignore-backups

# Hide matching patterns
uvx cosmofy fs ls my_bundle --hide '*.pyc'
uvx cosmofy fs ls my_bundle -I '*.pyc'  # ignore even with -a

# Long format (permissions, size, date)
uvx cosmofy fs ls my_bundle -l

# Human-readable sizes
uvx cosmofy fs ls my_bundle -lh
uvx cosmofy fs ls my_bundle --si  # powers of 1000

# Sort options
uvx cosmofy fs ls my_bundle --sort name   # default
uvx cosmofy fs ls my_bundle --sort size
uvx cosmofy fs ls my_bundle --sort time
uvx cosmofy fs ls my_bundle --sort extension
uvx cosmofy fs ls my_bundle -r  # reverse sort
```

### Filter Files

```bash
uvx cosmofy fs ls my_bundle '*.py'
uvx cosmofy fs ls my_bundle 'Lib/site-packages/*'
```

## View File Contents

```bash
uvx cosmofy fs cat my_bundle .args
uvx cosmofy fs cat my_bundle Lib/site-packages/my_module/__init__.py
```

### Multiple Files

```bash
uvx cosmofy fs cat my_bundle file1.py file2.py
```

### Encrypted Files

```bash
uvx cosmofy fs cat my_bundle secret.txt -p
uvx cosmofy fs cat my_bundle secret.txt --prompt  # prompt for password
```

### Files Starting with Dash

```bash
uvx cosmofy fs cat my_bundle -- -weird-filename.txt
```

## Add Files

```bash
uvx cosmofy fs add my_bundle file.py
uvx cosmofy fs add my_bundle dir/
```

### Options

```bash
# Overwrite existing files
uvx cosmofy fs add my_bundle file.py -f
uvx cosmofy fs add my_bundle file.py --force

# Change directory before adding
uvx cosmofy fs add my_bundle --chdir src/ my_module/

# Set destination prefix
uvx cosmofy fs add my_bundle file.py --dest Lib/site-packages/
```

## Remove Files

```bash
uvx cosmofy fs rm my_bundle old_file.py
```

### Options

```bash
# Ignore nonexistent files
uvx cosmofy fs rm my_bundle maybe.py -f
uvx cosmofy fs rm my_bundle maybe.py --force

# Remove directories recursively
uvx cosmofy fs rm my_bundle old_package/ -r
uvx cosmofy fs rm my_bundle old_package/ --recursive
```

## Get/Set .args

The `.args` file is special - it controls how Python starts.

```bash
# View current .args
uvx cosmofy fs args my_bundle

# Set .args
uvx cosmofy fs args my_bundle '-m my_module'
```

See [.args File](args-file.md) for more details.

## JSON Output

All `fs` commands support `--output-format json` for structured output:

```bash
# List files as JSON
uvx cosmofy fs ls my_bundle --output-format json

# Get file contents as JSON
uvx cosmofy fs cat my_bundle .args --output-format json

# Track what was added
uvx cosmofy fs add my_bundle file.py --output-format json

# Track what was removed
uvx cosmofy fs rm my_bundle old.py --output-format json
```

This is useful for scripting and parsing results programmatically.

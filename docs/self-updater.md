# Self-Updater

!!! warning "Experimental Feature"
    The self-updater is experimental. See [Security Considerations](#security-considerations) below.

The self-updater allows your cosmofy bundles to update themselves when new versions are released.

## How It Works

1. **Add updater** - `cosmofy updater add` embeds update logic and creates a receipt
2. **Publish receipt** - Upload the bundle and `.json` receipt to your release location
3. **Users update** - Running `--self-update` checks for and installs updates

## Adding the Updater

```bash
uvx cosmofy bundle
uvx cosmofy updater add dist/my_cmd  # produces dist/my_cmd.json
```

The `.json` receipt contains:

- Build date
- File hash for verification
- Download URLs

## Updating

Users can update by running:

```bash
my_cmd --self-update
```

The updater will:

1. Fetch the receipt from `--receipt-url`
2. Compare build dates
3. Download and verify the new binary
4. Replace the current binary

## Receipt Options

### Custom Paths

```bash
uvx cosmofy updater add my_bundle \
  --receipt ./custom/path/receipt.json \
  --receipt-url https://example.com/receipt.json \
  --release-url https://example.com/my_bundle
```

### Version String

```bash
uvx cosmofy updater add my_bundle --release-version "1.2.3"
```

By default, version is obtained by running `<BUNDLE> --version`.

### Process Options

```bash
# Skip copying cosmofy code (if already a dependency)
uvx cosmofy updater add my_bundle --no-copy

# Skip setting .args
uvx cosmofy updater add my_bundle --no-args
```

## Removing the Updater

```bash
uvx cosmofy updater remove my_bundle
```

## Checking for Updates

Check without installing:

```bash
uvx cosmofy updater check my_bundle
uvx cosmofy updater check my_bundle --receipt-url https://example.com/receipt.json
```

## Security Considerations

The self-updater verifies downloaded binaries against the hash in the receipt, but does not cryptographically verify the receipt itself.

**Current security model:**

- Binary integrity is verified via SHA-256 hash
- Receipt is fetched over HTTPS
- No receipt signing (planned for future release - see [#53](https://github.com/metaist/cosmofy/issues/53))

**Recommendations:**

- Host receipts on infrastructure you control
- Use HTTPS for all URLs
- Consider code signing for high-assurance scenarios

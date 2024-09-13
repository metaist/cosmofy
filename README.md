# cosmofy: Cosmopolitan Python Bundler

<p align="center">
  <a href="https://github.com/metaist/cosmofy/actions/workflows/ci.yaml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/metaist/cosmofy/.github/workflows/ci.yaml?branch=main&logo=github"/></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="PyPI" src="https://img.shields.io/pypi/v/cosmofy.svg?color=blue" /></a>
  <a href="https://pypi.org/project/cosmofy"><img alt="Supported Python Versions" src="https://img.shields.io/pypi/pyversions/cosmofy" /></a>
</p>

[Cosmopolitan apps](https://github.com/jart/cosmopolitan) are cross-platform binary files that work natively on Linux, macOS, and Windows. `cosmofy` is a tool to bundle your python project into a portable Cosmopolitan app.

```bash
# install
dest=~/.local/bin/cosmofy
curl -sSz $dest -o $dest -L https://github.com/metaist/cosmofy/releases/latest/download/cosmofy
chmod +x $dest

# bundle a single script
cosmofy my-script.py
# => produces my-script.com

# bundle a directory
cosmofy src/cosmofy --args '-m cosmofy --cosmo'
```

## License

[MIT License](https://github.com/metaist/cosmofy/blob/main/LICENSE.md)

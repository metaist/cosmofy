# Contributing

## Local Development

We recommend installing `uv`, but you can also use `pip`.

```bash
# get the code
git clone git@github.com:metaist/cosmofy.git
cd cosmofy
```

If using [`uv`](https://github.com/astral-sh/uv) (recommended):

```bash
uv sync --extra dev
. .venv/bin/activate
```

If using `pip`:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

As you work on the code, you should periodically run:

```bash
ds dev # check lint, type-checks, and run tests
```

This repo generally tries to maintain type-correctness (via `mypy` and `pyright`) and complete unit test coverage.

## Making a Release

Checkout `prod`:

```bash
git checkout prod
git merge --no-ff --no-edit main
```

Update top-most `__init__.py`:

```python
__version__ = "X.0.1"
```

Update `CHANGELOG.md`. To see recently closed issues run:

```bash
ds recent-closed
```

You can also look at the [unreleased](https://github.com/metaist/cosmofy/compare/prod...main) log too.

Sections order is: `Fixed`, `Changed`, `Added`, `Deprecated`, `Removed`, `Security`.

```markdown
---

[X.0.1]: https://github.com/metaist/cosmofy/compare/X.0.0...X.0.1

## [X.0.1] - XXXX-XX-XXT00:00:00Z

**Fixed**

**Changed**

**Added**

**Deprecated**

**Removed**

**Security**
```

### Final checks, tag, and push

```bash
export VER="X.0.1"

# final checks again every supported python version
ds dev-all # requires uv >= 0.3.0

# final build
ds docs build

# commit and push tags
ds release: $VER
```

[Create the release on GitHub](https://github.com/metaist/cosmofy/releases/new). The `pypi.yaml` workflow will attempt to publish it to PyPI.

"""A Cosmofy Receipt is metadata for self-updating programs."""

# std
from __future__ import annotations
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import List
from urllib.request import urlopen
import dataclasses
import hashlib
import json
import re
import subprocess

Checker = Callable[[str], bool]
"""Function that takes a `str` and returns a `bool` if it is ok."""

RECEIPT_SCHEMA = (
    "https://raw.githubusercontent.com/metaist/cosmofy/0.1.0/cosmofy.schema.json"
)
"""URI of Cosmofy Receipt Schema."""

RECEIPT_KIND = ("embedded", "published")
"""Valid values for `Receipt.kind`."""

RECEIPT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
"""Regex to validate `Receipt.date`."""

RECEIPT_ALGO = re.compile(r"^[a-z0-9-_]+$")
"""Regex to validate `Receipt.algo`."""

RECEIPT_HASH = re.compile(r"^[a-f0-9]+$")
"""Regex to validate `Receipt.hash`."""

DEFAULT_HASH = "sha256"
"""Default hashing algorithm."""

RE_VERSION = re.compile(rb"\d+\.\d+\.\d+(-[\da-zA-Z-.]+)?(\+[\da-zA-Z-.]+)?")
"""Regex for a semver-like version string."""


def datestr(date: datetime) -> str:
    """Return an ISO-8601 formatted date string.

    >>> datestr(datetime(2000, 1, 1, tzinfo=timezone.utc))
    '2000-01-01T00:00:00Z'
    """
    return date.astimezone(timezone.utc).isoformat()[:19] + "Z"


@dataclasses.dataclass
class Receipt:
    """Asset metadata."""

    schema: str = RECEIPT_SCHEMA
    """Receipt schema."""

    kind: str = RECEIPT_KIND[0]
    """Whether this receipt is full (published) or partial (embedded)."""

    date: str = datestr(datetime.now())
    """UTC date/time of this receipt."""

    algo: str = DEFAULT_HASH
    """Hashing algorithm."""

    hash: str = ""
    """Asset hash."""

    receipt_url: str = ""
    """Asset receipt URL."""

    release_url: str = ""
    """Asset download URL."""

    version: str = ""
    """Asset version."""

    def is_newer(self, other: Receipt) -> bool:
        """Return `True` if this receipt is newer than `other`."""
        return self.date > other.date

    def __str__(self) -> str:
        """Return `json`-encoded string."""
        return json.dumps(self.asdict())

    def asdict(self) -> Dict[str, str]:
        """Return `dict` representation of the receipt."""
        return {
            "$schema": self.schema,
            "kind": self.kind,
            "date": self.date,
            "algo": self.algo,
            "hash": self.hash,  # maybe empty
            "receipt_url": self.receipt_url,
            "release_url": self.release_url,
            "version": self.version,  # maybe empty
        }

    def is_valid(self) -> bool:
        """Return `True` if there are no issues with the receipt."""
        issues = Receipt.find_issues(self.asdict())
        return not sum((v for v in issues.values()), [])

    @staticmethod
    def find_issues(data: Dict[str, str]) -> Dict[str, List[str]]:
        """Return field names by issue that occurred during validation."""
        issues: Dict[str, List[str]] = {"missing": [], "unknown": [], "malformed": []}
        rules: Dict[str, Checker] = {
            "$schema": lambda v: v == RECEIPT_SCHEMA,
            "kind": lambda v: v in RECEIPT_KIND,
            "date": lambda v: bool(RECEIPT_DATE.match(v)),
            "algo": lambda v: bool(RECEIPT_ALGO.match(v)),
            "hash": lambda v: bool(RECEIPT_HASH.match(v)),
            "receipt_url": lambda v: bool(v.strip()),
            "release_url": lambda v: bool(v.strip()),
            "version": lambda v: bool(v.strip()),
        }
        embedded: Dict[str, Checker] = {
            "hash": lambda v: isinstance(v, str),
            "version": lambda v: isinstance(v, str),
        }

        kind = data.get("kind", "embedded")
        issues["unknown"] = [name for name in data if name not in rules]
        for name, rule in rules.items():
            if name not in data:
                issues["missing"].append(name)
                continue
            if name in embedded and kind == "embedded":
                rule = embedded[name]
            if not rule(data[name]):
                issues["malformed"].append(name)
        return issues

    def update(self, **values: str) -> Receipt:
        """Update this receipt with several values."""
        for name, value in values.items():
            setattr(self, name, value)
        return self

    def update_from(self, other: Receipt, *names: str, **values: str) -> Receipt:
        """Update this receipt from another receipt."""
        for name in names:
            setattr(self, name, getattr(other, name))
        return self.update(**values)

    @staticmethod
    def from_dict(data: Dict[str, str]) -> Receipt:
        """Return receipt from a `dict`."""
        issues = Receipt.find_issues(data)
        if sum((v for v in issues.values()), []):
            raise ValueError("Invalid receipt", issues)

        schema = data["$schema"]
        _data = {k: v for k, v in data.items() if k != "$schema"}
        return Receipt(schema=schema, **_data)

    @staticmethod
    def from_url(url: str) -> Receipt:
        """Return a Receipt from a URL."""
        with urlopen(url) as response:
            return Receipt.from_dict(json.load(response))

    @staticmethod
    def from_path(path: Path, version: str = "", algo: str = DEFAULT_HASH) -> Receipt:
        """Return hash and version for a `path`."""
        digest = hashlib.new(algo, path.read_bytes()).hexdigest()
        if not version:
            cmd = (f"{path.resolve()} --version",)
            out = subprocess.run(cmd, capture_output=True, check=True, shell=True)
            if match := RE_VERSION.search(out.stdout):
                version = match.group().decode("utf-8")
        return Receipt(algo=algo, hash=digest, version=version)

# std
from os import environ as ENV

DEFAULT_HASH = "sha256"
"""Default hashing algorithm."""

DEFAULT_TIMEOUT = 30  # seconds
"""Default network timeout."""

COSMOFY_TIMEOUT = int(ENV.get("COSMOFY_TIMEOUT", DEFAULT_TIMEOUT))
"""Network timeout (override via environment variable)."""

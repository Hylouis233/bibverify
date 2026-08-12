"""Public package metadata for Bibverify."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("bibverify")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.3.0"

__all__ = ["__version__"]

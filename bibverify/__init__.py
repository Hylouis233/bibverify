"""
BibVerify - A BibTeX citation verification tool

This package provides tools to verify BibTeX citations against multiple
academic databases including CrossRef, arXiv, and OpenAlex to detect
fake or incorrect references.
"""

__version__ = "0.1.0"
__author__ = "Hong Liu"
__license__ = "MIT"

from .verifier import BibVerifier, verify_bib_file, verify_bib_entry

__all__ = ["BibVerifier", "verify_bib_file", "verify_bib_entry"]

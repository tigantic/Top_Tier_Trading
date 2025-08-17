"""Verify exportable artifacts.

This script checks that the exportable artifacts (ZIP archive and
merged code file) exist in ``artifacts/exports``, computes their
SHA256 checksums and sizes, and prints them.  It returns a non-zero
exit code if any expected file is missing.

Usage::

    python scripts/verify_exportables.py

This tool can be invoked in CI after building exportables to ensure
provenance.  It does not compare against predetermined values;
instead, it reports the current checksums and sizes for manual
verification.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

EXPORT_DIR = Path("artifacts/exports")
# List of expected exportable artifact filenames.  Include both
# release candidate and general‑availability names for flexibility.
FILES = [
    "trading_platform_full_update_final.zip",
    "trading_platform_full_code.txt",
    "trading_platform_v1.0.0_full.zip",
    "trading_platform_v1.0.0_code.txt",
]


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify() -> bool:
    ok = True
    for fname in FILES:
        path = EXPORT_DIR / fname
        if not path.exists():
            print(f"Missing exportable: {path}")
            ok = False
        else:
            size = path.stat().st_size
            checksum = sha256sum(path)
            print(f"{fname}: size={size}, sha256={checksum}")
    return ok


def main() -> None:
    ok = verify()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

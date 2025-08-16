"""Generate a coverage badge snippet.

This script reads ``coverage.xml`` produced by the test suite and
emits a Markdown image tag pointing at a Shields.io badge with the
overall coverage percentage.  If no coverage file is found, the
badge will indicate "N/A".

Usage::

    python scripts/coverage_badge.py > coverage_badge.md

In CI, you can capture the output and include it in documentation.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET


def read_coverage() -> str:
    """Return coverage percentage string, or 'N/A' if unavailable."""
    cov_file = "coverage.xml"
    if not os.path.isfile(cov_file):
        return "N/A"
    try:
        tree = ET.parse(cov_file)
    except Exception:
        return "N/A"
    root = tree.getroot()
    rate = root.get("line-rate")
    if rate is None:
        return "N/A"
    try:
        percent = float(rate) * 100
    except Exception:
        return "N/A"
    return f"{percent:.1f}"


def main() -> None:
    pct = read_coverage()
    if pct == "N/A":
        color = "lightgrey"
        label = "coverage-N/A"
    else:
        # Choose green for >=80, yellow for >=50, red otherwise
        val = float(pct)
        if val >= 80:
            color = "brightgreen"
        elif val >= 50:
            color = "yellow"
        else:
            color = "red"
        label = f"coverage-{pct}%"
    url = f"https://img.shields.io/badge/{label}-{color}.svg"
    print(f"![Coverage]({url})")


if __name__ == "__main__":
    main()
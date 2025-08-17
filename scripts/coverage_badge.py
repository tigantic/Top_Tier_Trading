from __future__ import annotations

import os

from defusedxml import ElementTree as ET  # secure variant


def read_coverage(cov_file: str) -> float:
    try:
        tree = ET.parse(cov_file)
    except Exception:
        return 0.0
    root = tree.getroot()
    # adapt to your coverage.xml schema; example for Cobertura:
    try:
        line_rate = float(root.get("line-rate", "0"))
        return line_rate * 100.0
    except Exception:
        return 0.0


def main() -> None:
    cov_file = os.getenv("COVERAGE_XML", "coverage.xml")
    pct = read_coverage(cov_file)
    print(f"coverage: {pct:.2f}%")


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys

from defusedxml import ElementTree as ET  # secure variant


def summarize(file_path: str) -> tuple[float, float]:
    try:
        tree = ET.parse(file_path)
    except Exception:
        return (0.0, 0.0)
    root = tree.getroot()
    try:
        line_rate = float(root.get("line-rate", "0"))
        branch_rate = float(root.get("branch-rate", "0"))
        return (line_rate * 100.0, branch_rate * 100.0)
    except Exception:
        return (0.0, 0.0)


def main() -> None:
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"
    line, branch = summarize(xml_path)
    print(f"Lines: {line:.2f}% Branches: {branch:.2f}%")


if __name__ == "__main__":
    main()

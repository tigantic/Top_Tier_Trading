# Badges Reference

This file summarises the status badges used in the repository.  These badges
appear in the root `README.md` and provide quick insight into project health.

| Badge | Description |
|------|-------------|
| ![CI Status](https://img.shields.io/badge/ci-passing-brightgreen.svg) | Indicates that the continuous integration pipeline is passing. |
| ![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg) | Supported Python versions. |
| ![License](https://img.shields.io/badge/license-MIT-lightgrey.svg) | Specifies the open-source license. |
| ![Coverage](https://img.shields.io/badge/coverage-N/A-lightgrey.svg) | Code coverage percentage.  In offline mode this badge shows `N/A`.  In CI this badge is updated to reflect the coverage reported in `coverage.xml`. |
| **Release Candidate** | The version information appears in the README.  For RC1 this is `1.0.0-rc1`. |

You can regenerate the coverage badge locally using:

```bash
python scripts/coverage_badge.py
```

The output can be copied into the README or other documentation.
"""Pytest configuration for path setup.

The test suite requires access to modules located under ``workers/src``.
When pytest is executed as an installed script, the repository root is not
automatically added to ``sys.path``.  This file ensures that both the project
root and the ``workers/src`` directory are available for imports during test
collection.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Ensure the project root is at the front of sys.path so that packages like
# ``workers.src`` can be imported regardless of how pytest is invoked.
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)


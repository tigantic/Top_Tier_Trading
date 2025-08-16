"""Top-level package for worker-related code.

This file ensures that the ``workers`` directory is treated as a Python
package, allowing imports such as ``workers.src.workers`` to resolve
correctly when running tests or other tooling.

It also exposes commonly used subpackages (``services``, ``strategies``
and ``clients``) at the top level so that test modules can simply import
``workers.services`` without needing the intermediate ``src`` prefix.
"""

from __future__ import annotations

import importlib
import sys

# Re-export selected subpackages from ``workers.src.workers`` for
# convenience.  Missing subpackages are ignored to keep imports lazy.
for _name in ("services", "strategies", "clients"):
    try:
        _module = importlib.import_module(f"{__name__}.src.workers.{_name}")
    except Exception:  # pragma: no cover - best effort re-export
        continue
    else:
        sys.modules[f"{__name__}.{_name}"] = _module

# The package exposes no additional public API at the top level.



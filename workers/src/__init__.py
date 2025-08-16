"""
Make `src` a package under `workers`.

This file is intentionally empty but necessary for Python to treat
`workers/src` as a package so that modules under it (e.g.
`workers.src.workers`) can be imported using the dotted path.
"""
__all__ = []

"""
Package marker for the top-level `workers` module.

Having this file ensures Python recognises the `workers` directory
as a package.  Without it, imports like `from workers.src.workers`
would fail when running tests or scripts.
"""
__all__ = []

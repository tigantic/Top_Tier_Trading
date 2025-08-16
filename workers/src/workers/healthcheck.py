"""
Healthcheck module for the workers container.

This script is used by the Docker healthcheck to verify that the worker
container can start and import required modules.  It does not perform a
comprehensive liveness probe; that responsibility belongs to individual
services.
"""

import sys


def main() -> None:
    try:
        # Attempt to import the worker modules to ensure dependencies are satisfied
        import workers  # noqa: F401
    except Exception as exc:  # pragma: no cover - healthcheck only
        print(f"Import error: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()

"""
Healthcheck script for the backtester container.

This simply imports the backtester package to ensure that dependencies are
installed and the module can be loaded.  It is used by the Docker
healthcheck specified in the Dockerfile.
"""

import sys


def main() -> None:
    try:
        import backtester  # noqa: F401
    except Exception as exc:
        print(f"Backtester import error: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()

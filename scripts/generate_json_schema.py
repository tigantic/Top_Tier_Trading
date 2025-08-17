"""
generate_json_schema
====================

This script exports JSON Schema definitions for the domain models used
in the trading platform.  It uses Pydantic's built‑in JSON schema
generator to produce schemas for ``OrderRequest``, ``OrderResponse``,
``Position`` and ``Account`` models defined in
``workers/src/workers/services/models.py``.  The resulting schema can
be used to generate clients in other languages (e.g., TypeScript)
using code generation tools such as `json-schema-to-typescript`.

Usage
-----

Run this script from the project root and specify an output file:

.. code-block:: bash

    python scripts/generate_json_schema.py --out schemas.json

If no output file is provided, the schema will be printed to stdout.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Type

# Domain models are defined in workers.models.  Adjust the import path
from workers.models import Account, OrderRequest, OrderResponse, Position  # type: ignore

try:
    from pydantic import BaseModel
except ImportError as e:
    raise SystemExit(
        "pydantic is required for generating schemas. Install it with `pip install pydantic`"
    ) from e


def collect_models() -> Dict[str, Type[BaseModel]]:
    return {
        "OrderRequest": OrderRequest,
        "OrderResponse": OrderResponse,
        "Position": Position,
        "Account": Account,
    }


def generate_schema(models: Dict[str, Type[BaseModel]]) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {},
    }
    for name, model in models.items():
        model_schema = model.model_json_schema()  # type: ignore[attr-defined]
        # Pydantic returns schema with title at top level; we normalize under definitions
        schema["definitions"][name] = model_schema
    return schema


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate JSON schemas for domain models.")
    ap.add_argument("--out", help="Output file path. Defaults to stdout if omitted.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    models = collect_models()
    schema = generate_schema(models)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        print(f"Schema written to {args.out}")
    else:
        print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()

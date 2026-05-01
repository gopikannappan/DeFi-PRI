#!/usr/bin/env python3
"""
validate.py — validate all protocol JSONs against the schema.

Run from the repo root:
    python3 scripts/validate.py

Requires: jsonschema (pip install jsonschema)
"""

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("Missing dependency. Install with: pip install jsonschema")
    sys.exit(1)


def main():
    repo_root = Path(__file__).parent.parent
    schema_path = repo_root / "schema" / "governance-graph-v0.2.json"
    protocols_dir = repo_root / "protocols"

    with schema_path.open() as f:
        schema = json.load(f)
    validator = Draft7Validator(schema)

    print(f"Schema: {schema['$id']}")
    print()

    protocols = sorted(protocols_dir.glob("*.json"))
    passed = failed = 0

    for fp in protocols:
        with fp.open() as f:
            data = json.load(f)
        errors = list(validator.iter_errors(data))
        if not errors:
            slug = data.get("identity", {}).get("slug", "?")
            sv = data.get("meta", {}).get("schema_version", "?")
            parent = data.get("identity", {}).get("parent_protocol")
            market = data.get("identity", {}).get("market_id")
            ident = f"{parent}/{market}" if parent else slug
            print(f"  PASS  {fp.name:<25} (schema={sv}, id={ident})")
            passed += 1
        else:
            print(f"  FAIL  {fp.name:<25} ({len(errors)} errors)")
            for e in errors[:5]:
                print(f"        - {e.message} at {list(e.path)}")
            failed += 1

    print()
    print(f"Total: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

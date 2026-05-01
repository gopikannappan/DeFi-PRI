#!/usr/bin/env python3
"""
Migration v0.1 → v0.2

Changes applied:
1. identity.parent_protocol: null  (new optional field)
2. identity.market_id: null  (new optional field)
3. meta.schema_version: "0.1" → "0.2"
4. emergency_controls[*].is_one_shot: bool  (default false)
5. emergency_controls[*].expires_at: null  (default null)

Special-case migrations for known one-shot emergency capabilities:
- Lido GateSeal: is_one_shot=true, expires_at=null (re-deployable after fire)
- Curve older pools kill_me: covered in note since this is a per-pool field, not in main records yet

No splits applied automatically — those are content decisions, not migrations.
Lido stays as 'lido'. Aave Main stays as 'aave-v3'. Curve stays as 'curve'.
Splits will happen organically as we add 'aave-v3-prime', 'curve-crvusd' etc.
The schema NOW supports them, but existing records aren't forcibly split.
"""

import json
import sys
from pathlib import Path

PROTOCOL_FILES = [
    "example-uniswap-v3.json",
    "example-aave-v3.json",
    "example-curve.json",
    "example-lido.json",
]

# Special-case marking known one-shot emergency mechanisms
ONE_SHOT_MARKERS = {
    "example-lido.json": [
        # Match by function string
        "seal (GateSeal)",
        "extend_seal (Reseal Manager)",
    ],
}


def migrate(filepath: Path) -> dict:
    with filepath.open() as f:
        data = json.load(f)

    # 1 & 2: Add parent_protocol and market_id (null for existing records)
    if "parent_protocol" not in data["identity"]:
        data["identity"]["parent_protocol"] = None
    if "market_id" not in data["identity"]:
        data["identity"]["market_id"] = None

    # 3: Bump schema_version
    data["meta"]["schema_version"] = "0.2"

    # 4 & 5: Add is_one_shot and expires_at to all emergency_controls
    one_shot_funcs = ONE_SHOT_MARKERS.get(filepath.name, [])
    for ec in data.get("emergency_controls", []):
        if "is_one_shot" not in ec:
            ec["is_one_shot"] = ec["function"] in one_shot_funcs
        if "expires_at" not in ec:
            ec["expires_at"] = None

    return data


def main():
    base = Path("/home/claude/pri-schema")

    for fname in PROTOCOL_FILES:
        fp = base / fname
        if not fp.exists():
            print(f"  SKIP {fname} (not found)")
            continue

        # Backup
        backup = fp.with_suffix(".v01.json.backup")
        backup.write_text(fp.read_text())

        # Migrate
        migrated = migrate(fp)

        # Write
        with fp.open("w") as f:
            json.dump(migrated, f, indent=2)
            f.write("\n")

        print(f"  MIGRATED {fname}")

    print("\nDone. v0.1 backups preserved as *.v01.json.backup")


if __name__ == "__main__":
    main()

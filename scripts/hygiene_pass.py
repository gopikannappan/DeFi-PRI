#!/usr/bin/env python3
"""
hygiene_pass.py — clean protocol JSONs for public release.

Replaces TBD_* placeholder strings with explicit "unverified" markers,
and removes/cleans any conversation-style notes that referenced internal
research processes.

Run before publishing the repo.
"""

import json
import re
from pathlib import Path

PROTOCOLS_DIR = Path("/home/claude/repo/protocols")


def clean_value(v):
    """Replace TBD_* placeholders with cleaner unverified markers."""
    if isinstance(v, str):
        # TBD_ patterns -> human-readable unverified flags
        if v.startswith("TBD_"):
            slug = v[4:].replace("_", " ")
            return f"unverified:{slug}"
        return v
    if isinstance(v, dict):
        return {k: clean_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [clean_value(x) for x in v]
    return v


def clean_notes(v):
    """Strip references to verify.py runs and conversation artifacts from notes."""
    if isinstance(v, str):
        v = v.replace("Run verify.py to populate.", "")
        v = v.replace("Run verify.py to populate", "")
        v = re.sub(r"\s+", " ", v).strip()
        return v
    if isinstance(v, dict):
        return {k: clean_notes(val) for k, val in v.items()}
    if isinstance(v, list):
        return [clean_notes(x) for x in v]
    return v


def main():
    files = sorted(PROTOCOLS_DIR.glob("*.json"))
    for fp in files:
        with fp.open() as f:
            data = json.load(f)
        cleaned = clean_notes(clean_value(data))
        with fp.open("w") as f:
            json.dump(cleaned, f, indent=2)
            f.write("\n")
        print(f"cleaned {fp.name}")


if __name__ == "__main__":
    main()

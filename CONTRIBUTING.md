# Contributing to DPRI

PRs welcome. This is research, not a service — there's no SLA on issue response, but legitimate corrections and additions get merged.

## Common contribution patterns

### 1. Fact corrections

If a value in a protocol JSON doesn't match what's actually on-chain, open a PR.

- Update the relevant field in `protocols/<slug>.json`.
- Run `python3 scripts/validate.py` to confirm the JSON still validates.
- Run `python3 scripts/compute_scores.py` and update `scores.json` if the score changes.
- In the PR description: include the block number you read at, the on-chain query that confirms the new value, and a one-line explanation.

### 2. Adding a new protocol

The schema accommodates EVM and Solana protocols out of the box. For other VMs, propose schema extensions in an issue first.

- Create `protocols/<slug>.json` following the structure of an existing protocol.
- Map: `identity`, `admin_surface`, `upgrade_paths`, `emergency_controls`, `timelocks`, `oracles`, `meta`.
- Run `python3 scripts/validate.py` until it passes.
- Add the protocol to `scripts/compute_scores.py` with each sub-score derived from the JSON per the methodology document.
- Open a PR. Include in the description: which methodology breakpoints applied, why, and any judgment calls.

### 3. Methodology critiques

Methodology v0.1 has known limitations (it doesn't account for blast radius; it under-weights no-bypass guarantees). New critiques are welcome.

- Open an issue with: the proposed change to a scoring breakpoint, the protocols whose scores would change as a result, and your reasoning.
- Methodology changes will batch into v0.2. Score changes between methodology versions will be explicit.

### 4. Verification updates

Multisig signers rotate. Thresholds change. Timelock delays update. The protocol JSONs will drift from on-chain reality over time.

- Re-run `scripts/verify_evm_solana.py` and `scripts/verify_evm_extended.py`.
- Compare output against the protocol JSONs.
- Open a PR with the updated values and the block number you verified at.

## What won't get merged

- Score changes without methodology justification.
- New scoring categories without showing the impact across all 10 protocols.
- Protocol additions without runnable verification queries (the JSON has to be reproducible from on-chain reads).
- Changes that remove the methodology's reproducibility guarantee (e.g., introducing subjective inputs not derivable from JSON fields).

## Style

- One protocol JSON per file.
- Schema field order follows the schema definition.
- Comments and explanatory notes go in `_note` fields within the JSON, not in code comments.
- Keep `_note` fields factual and source-cited where possible.

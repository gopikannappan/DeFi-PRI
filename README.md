# DeFi Protocol Risk Index (DPRI)

A transparent, reproducible scoring methodology for DeFi protocol governance.

DPRI maps the **on-chain governance trust model** of major DeFi protocols and produces a comparable risk score from observable contract state. The methodology is published. The data is published. Every score in this repo can be reproduced from the JSON plus the methodology document.

This is v0.1: 10 protocols mapped, schema v0.2, methodology v0.1. Scores were verified against on-chain state in April 2026.

---

## TL;DR

| Rank | Protocol | Score | Band | Pattern |
|---:|---|---:|:---:|---|
| 1 | Curve | 90 | A | token-bound DAO |
| 2 | Lido | 88 | A | token-bound DAO |
| 3 | Uniswap | 84 | B | token-bound DAO |
| 4 | Aave | 82 | B | token-bound DAO |
| 5 | Sky (formerly Maker) | 81 | B | token-bound DAO |
| 6 | EigenLayer | 65 | C | multisig only |
| 7 | GMX | 58 | C | multisig + advisory DAO |
| 8 | Jito | 52 | D | hybrid |
| 9 | Pendle | 50 | D | hybrid |
| 10 | Jupiter Aggregator | 47 | D | hybrid |

Methodology in [`methodology/scoring-v0.1.md`](methodology/scoring-v0.1.md). Per-protocol JSONs in [`protocols/`](protocols/). Compute the scores yourself with `python3 scripts/compute_scores.py`.

---

## Why this exists

"DAO-governed" is doing a lot of work in DeFi marketing. It gets applied to protocols where token holder votes bind every on-chain action (Curve, Lido, Sky), to protocols where the DAO controls treasury but a multisig controls upgrades (Jupiter, Pendle, Jito), to protocols where the DAO is purely advisory and a multisig executes (GMX), and to protocols that have no token voting at all (EigenLayer).

These are different trust models. They should not produce the same risk score.

PRI separates them into four categories and grades each protocol on five sub-dimensions:

- **Governance binding** — does token voting actually constrain on-chain action, or is it advisory?
- **Time buffer** — how much time exists between a malicious decision and irreversible execution?
- **Authority distribution** — how concentrated is the power to act?
- **Emergency design** — quality of pause/kill mechanisms; can they trap user funds?
- **Code mutability** — can the core implementation be changed at all, and how?

Each sub-score is derived from observable schema fields with documented breakpoints. The composite is a weighted average. Bands run A (85–100) to E (0–39).

---

## Repository layout

```
schema/                     JSON schema for the governance graph
  governance-graph-v0.2.json

protocols/                  One JSON per protocol, validated against schema
  aave.json
  curve.json
  eigenlayer.json
  gmx.json
  jito.json
  jupiter.json
  lido.json
  pendle.json
  sky.json
  uniswap.json

methodology/                The published scoring rubric and schema changelog
  scoring-v0.1.md
  schema-changelog.md

scripts/                    Reproduce, verify, validate
  compute_scores.py         Compute scores from the protocol JSONs
  validate.py               Validate JSONs against the schema
  verify_evm_solana.py      Read on-chain state via public RPCs
  verify_evm_extended.py    Extended verification (timelock roles, etc.)
  migrate_v01_to_v02.py     Schema migration script

findings/                   Per-protocol research notes (subset)
  aave.md, curve.md, gmx.md, lido.md

scores.json                 Pre-computed scores for v0.1 release
```

---

## Reproducing the scores

```bash
git clone https://github.com/your-handle/protocol-risk-index
cd protocol-risk-index

# Validate that all protocol JSONs conform to the schema
pip install jsonschema
python3 scripts/validate.py

# Recompute the scores from the JSONs
python3 scripts/compute_scores.py
```

The output of `compute_scores.py` should match `scores.json` exactly. If it doesn't, file an issue.

---

## Reproducing the on-chain verification

The protocol JSONs were verified against Ethereum, Arbitrum, and Solana mainnet in April 2026. Multisig configurations, timelock delays, role assignments, and proxy admin slots were read directly from chain.

```bash
pip install web3 eth_utils
python3 scripts/verify_evm_solana.py
python3 scripts/verify_evm_extended.py
```

Output is saved to `verification_results.json`. Compare against the values in the protocol JSONs. If anything has drifted (multisig signers rotated, threshold changed, timelock delay updated, etc.), open a PR.

The verification scripts are the audit trail. They are also how the dataset stays current.

---

## What this measures

DPRI scores the **on-chain governance trust model**. Specifically:

- The structure of admin authority — who holds upgrade keys, pause keys, parameter-change keys.
- The temporal buffer between a malicious decision and irreversible execution.
- The distribution of authority across multisigs, DAOs, and timelocks.
- The design and reach of emergency controls.
- The mutability of the core implementation.

## What this does NOT measure

DPRI is one signal among several. It does not score:

- **Code quality.** A protocol with great governance can still have exploitable bugs. Audits are a separate domain.
- **Economic security.** Liquidity, liquidation engines, peg stability, oracle robustness are out of scope.
- **Token distribution.** Voter turnout, whale concentration, and governance attack economics are downstream of the structures PRI maps but not directly scored.
- **Off-chain trust surface.** Validator keys, oracle infrastructure, daemon software, MPC custody arrangements. These are noted in the JSONs where significant (Lido, GMX, Jupiter, Jito) but not scored in v0.1.
- **Track record.** Time in market and incident history are protocol metadata, not scored.
- **MEV and liveness properties.** Out of scope.

A high DPRI score is a necessary-but-not-sufficient signal for trusting a protocol with material capital. Read the full record, not just the number.

---

## How to read a protocol JSON

Every protocol JSON has the same structure:

- `identity` — slug, name, category, chain(s), parent_protocol if applicable
- `admin_surface` — every privileged role with its controller (multisig, timelock, DAO, EOA, etc.)
- `upgrade_paths` — how the implementation can be changed
- `emergency_controls` — pause, kill, freeze functions and their callers
- `timelocks` — delay buffers protecting privileged actions
- `oracles` — price feeds and their administrators
- `meta` — schema version, last indexed block, sources

The schema (`schema/governance-graph-v0.2.json`) is the formal definition. Examples of every pattern are in the protocol JSONs.

---

## Methodology versioning

- **v0.1** (current) — initial release with 5-category rubric, 10 protocols mapped.
- v0.2 (planned) — should account for blast radius (currently penalizes stateless protocols like aggregators) and reward no-bypass guarantees (currently under-scores Sky's non-bypassable Pause).

Score changes between methodology versions will be explicit and documented. Comparing scores across methodology versions is not meaningful without re-applying the new rubric to all protocols.

The schema is also versioned independently (currently v0.2). Schema changes are additive and migration scripts are provided.

---

## Contributing

PRs welcome. Common contribution patterns:

- **Fact corrections.** If on-chain state in a protocol JSON doesn't match what's actually on-chain, open a PR with the corrected JSON and a one-line note explaining what changed.
- **New protocols.** Map a protocol against the v0.2 schema, run `validate.py`, run `compute_scores.py`, open a PR. The schema enforces consistency; the methodology determines the score.
- **Methodology critiques.** If you think a scoring breakpoint is wrong, open an issue with the proposed change and the protocols it would re-rank. Methodology debates are welcome and expected.
- **Verification updates.** If you re-run the verification scripts and find drift (signers rotated, thresholds changed, timelock delays updated), open a PR with the new values and the block number you read at.

This is research, not a service. There is no SLA on issue response. Quarterly refreshes are the expected cadence.

---

## License

- **Data** (`schema/`, `protocols/`, `scores.json`, `methodology/`, `findings/`): Creative Commons CC0 1.0 Universal — public domain dedication. Use it for anything, including commercial products, without attribution.
- **Code** (`scripts/`): MIT License.

The intent: anyone can fork this dataset into their own dashboard, indexer, risk engine, or research paper without permission. If the work is useful, the highest-value outcome is for it to propagate.

---

## Citation

If you use DPRI in published work:

```
DeFi Protocol Risk Index v0.1 (April 2026).
https://github.com/gopikannappan/DeFi-PRI/
```

---

## Related work / honorable mentions

- **DeFiSafety** — process-quality scores for DeFi protocols. Different methodology, broader scope, less granular on governance specifically.
- **Exponential.fi** — protocol risk grading with a focus on platform risk; methodology not fully open.
- **Aave Permissions Book** (BGD Labs) — comprehensive map of Aave V3 admin authority. Inspiration for the depth of detail in `protocols/aave.json`.

DPRI is opinionated where these are general, transparent where they are partial, and limited in scope where they are broad. It complements rather than replaces them.

---

## Author

By Gopi Kannappan. Reach me at (https://x.com/gopikannappan).

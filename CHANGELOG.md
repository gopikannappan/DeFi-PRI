# Changelog

## v0.1 — Initial release (April 2026)

First public release of the Protocol Risk Index.

### Included
- 10 protocols mapped: Curve, Lido, Uniswap, Aave, Sky (formerly Maker), EigenLayer, GMX, Jito, Pendle, Jupiter Aggregator
- Schema v0.2 with multi-market protocol support and one-shot/expiring emergency capability fields
- Scoring methodology v0.1 with 5 categories: governance binding, time buffer, authority distribution, emergency design, code mutability
- Verification scripts for Ethereum, Arbitrum, and Solana via public RPCs
- Pre-computed scores in `scores.json`

### Verification snapshot
- All EVM protocol data verified against Ethereum and Arbitrum mainnet via public RPCs in April 2026
- Solana protocols verified via Solscan and direct RPC queries
- EigenLayer role assignments verified by decoding `scheduleBatch`/`executeBatch` transactions on the primary timelock
- Jupiter and Jito multisig configurations verified via Squads V3 program account inspection
- 4 protocols had public-doc claims that did not match on-chain reality at verification time. Discrepancies are documented in the protocol JSONs.

### Known limitations of v0.1 methodology
- Does not account for blast radius. Stateless protocols (aggregators, routers) score lower than custodial protocols at equivalent governance maturity, which can be misleading.
- Under-weights no-bypass timelock guarantees. Sky's non-bypassable Pause should score better than the current rubric reflects.
- Does not score off-chain trust surface (validator keys, oracle infrastructure, MPC custody arrangements). These are noted in the JSONs but not scored.

These are the planned focus of methodology v0.2.

## Planned for v0.2

### Methodology
- `blast_radius_weight` modifier for stateless protocols.
- Bonus for non-bypassable timelocks.
- Penalty for verification gaps that can't be resolved from public sources.

### Schema (v0.3)
Four candidates locked from v0.1 mapping work, ready for promotion:
- `governance_binding` enum (token-bound DAO / hybrid / multisig + advisory DAO / multisig only / immutable)
- `asymmetric_multisig_thresholds` for pause vs. unpause patterns
- `role_based.members[]` structure for AccessControl-style permissions
- `trust_surface[]` for off-chain dependencies

### Coverage
- Add Spark and Grove as Sky SubDAOs (parent_protocol pattern from v0.2 schema).
- Add Aave V3 Prime and Lido markets as parent_protocol siblings.
- Map 5–10 additional protocols based on community priority.

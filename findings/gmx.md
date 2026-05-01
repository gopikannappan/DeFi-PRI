# GMX V2 Mapping — Findings & Schema Observations

## What the mapping confirmed

**Schema v0.2 generalizes well to multi-chain protocols** with a small bug fix (deployment_block now nullable). The `chains[]` array handles Arbitrum + Avalanche + Botanix elegantly with per-chain contract addresses. This validates the "one record, multi-chain" decision made when the schema was first designed.

**GMX V2's architecture is structurally similar to Aave** in one important way: both use a role-based access control contract (RoleStore for GMX, ACLManager for Aave) as the central permission system. The schema's `controller_type: "role_based"` and `controller_type: "multisig"` fields handle the GMX patterns without any new fields needed.

## The single most important finding from GMX

**GMX V2 is the first protocol mapped where on-chain authority is a multisig — NOT a token-bound DAO.** GMX token holders vote on Snapshot.org, but those votes are advisory only. They do not bind any on-chain action. The actual on-chain authority chain is:

```
Multisig signers (4+ of N) → Multisig → Timelock (12h) → DataStore/RoleStore → protocol contracts
```

Compare to the four protocols mapped previously:

| Protocol | Token holders bind on-chain action? |
|---|---|
| Uniswap V3 | Yes (UNI → Governor Bravo → Timelock) |
| Aave V3 | Yes (AAVE → Governance V3 → Executor) |
| Curve | Yes (veCRV → Aragon Voting → Aragon Agent) |
| Lido | Yes (LDO → Aragon Voting → DG → Executor) |
| **GMX V2** | **No (GMX → Snapshot signal → multisig discretion)** |

This is a fundamental trust model difference. GMX has good operational hygiene — multisig with 4+ signers, 12h timelock, role separation, demonstrated emergency response — but it is more centralized than its peers in the strict sense. The signers are accountable to the community by reputation and Snapshot signal, not by smart contract enforcement.

**The dashboard must make this distinction visible.** Two protocols can both have "DAO" in their description while having materially different governance models. A risk score that doesn't separate "binding on-chain governance" from "advisory off-chain signaling with multisig execution" would mislead users.

## Schema v0.3 candidate

Add a field to `meta` (or to identity) that captures the binding nature of governance:

```yaml
governance_binding: enum
  - on_chain_token_voting     # Uniswap, Aave, Curve, Lido
  - off_chain_signaling_with_multisig_execution  # GMX
  - multisig_only             # No DAO at all
  - immutable                 # No governance possible
```

Or as a binary `governance_is_binding_onchain: bool`. Defer until at least one more protocol confirms the GMX pattern (Pendle? possibly. EigenLayer? unlikely — uses on-chain voting).

## Other schema observations from GMX

### 1. Per-chain admin separation under one brand

GMX V2 on Arbitrum and on Avalanche have separate RoleStore contracts and (likely) separate admin multisigs, even though they share the brand. The schema's `chains[]` array captures this. But for risk scoring, a compromise on Avalanche shouldn't taint the Arbitrum deployment's score — they're operationally independent despite shared branding.

**Implication:** the scoring layer should produce per-chain scores when the protocol has chain-isolated admin trees. This is more nuanced than "one score per protocol" — Aave V3 has chain-isolated executors too (Polygon executor is separate from Ethereum executor) but governance flows from one source. GMX may have multisigs with overlapping signers but independent contract ownership. Indexer needs to compare signer sets across chains.

### 2. Immutable handlers + persistent state

GMX V2's pattern: handlers (DepositHandler, OrderHandler, etc.) are immutable contracts. The DataStore and RoleStore are immutable in practice. "Upgrades" happen by deploying new handlers and updating references in DataStore via TIMELOCK_ADMIN config changes.

This is structurally similar to Curve's "deploy new pools, migrate liquidity" pattern but operationally different — GMX users don't need to do anything to migrate when handlers change; their existing positions and funds aren't affected, only the routing logic is updated. Existing positions remain in OrderVault/DepositVault, which are persistent.

The schema's existing `upgrade_paths[].mechanism: "immutable"` captures this acceptably with notes. No schema change needed.

### 3. 12-hour timelock is short by external risk-review standards

DefiSafety, Exponential.fi, and similar reviewers consistently flag timelocks under 48 hours as suboptimal. GMX's 12h is documented as deliberate ("respond quickly to any issues") but objectively shorter than the four other protocols mapped:

| Protocol | Min Timelock | 
|---|---|
| Uniswap V3 | 2 days |
| Aave V3 | 1 day (Lvl1) / 7 days (Lvl2) |
| Curve | 3 days (per-pool) + 1 week vote |
| Lido | 3 days (DG min) |
| GMX V2 | 12 hours |

This is a real risk-score input, not a stylistic complaint. Score input addition: `min_timelock_delay_seconds` already exists in the schema; the scoring function should weight 12h less than 24h, less than 48h, less than 72h+.

## Pattern across five protocols

| Pattern | Uniswap V3 | Aave V3 | Curve | Lido | GMX V2 |
|---|---|---|---|---|---|
| Core implementation | Immutable | Upgradeable proxy | Immutable per-pool | Upgradeable proxy | Immutable handlers |
| Governance binding on-chain | Yes (Governor Bravo) | Yes (Gov V3) | Yes (Aragon) | Yes (Aragon + DG) | **No (Snapshot advisory)** |
| Timelock min | 2d | 1d / 7d tiered | 3d + 1w vote | 3d (dynamic) | 12h |
| Emergency model | None | Pause-only multisig | Multi-action DAO | Multi-layer | Multisig + 12h timelock |
| Pause traps funds | n/a | No | No | Temporarily yes | No |
| Off-chain trust | None | None | Minimal | Significant | Significant (oracle keepers, order keepers, multisig) |

## Pattern emerging across the dashboard

We have 5 protocols. We have 4 categories (DEX, Lending, LST, Derivatives). We have 2 governance models (token-bound DAO, multisig-with-advisory-DAO). 

The dashboard categorization is starting to reveal:

- **Token-bound on-chain DAOs**: Uniswap, Aave, Curve, Lido — different mechanisms but same trust model
- **Multisig-with-advisory-DAO**: GMX (and likely others coming up — Pendle is candidate)
- **Pure multisig**: probably MakerDAO sub-systems, possibly some Solana protocols

Risk scoring should recognize these as 3 different bands. Within each band, the per-protocol score reflects implementation quality.

## v0.3 candidates running tally

| Candidate | Confirmations | New from GMX? |
|---|---|---|
| `dynamic_timelock` | Lido (1) | No |
| `asymmetric_multisig_thresholds` | Lido (1) | No |
| `role_based.members[]` structure | Aave + Lido implicit (1.5) | Aave + GMX both have it now (2.5) |
| `trust_surface[]` for off-chain deps | Lido (1) | GMX adds significant off-chain trust (oracle keepers, order keepers) — could now be 2 |
| **NEW: governance_binding enum** | **GMX (1)** | **Yes** |

If EigenLayer (next priority candidate after this) confirms either the asymmetric multisig pattern OR the off-chain trust surface, we're at 2/5 confirmations on multiple candidates. Plan v0.3 around mapping #7 or #8.

## What I deliberately did NOT verify

I used `TBD_admin_multisig_arbitrum` and `TBD_timelock_arbitrum` as placeholder addresses for the actual multisig and timelock contracts. The reason: GMX V2's exact admin multisig addresses are not in publicly-cited references — they're recoverable by querying RoleStore.getRoleMembers(ROLE_ADMIN) and reading the DataStore for timelock references, but I couldn't pull live chain state in this session.

For the dashboard to actually publish the GMX record, the indexer must:
1. Read `RoleStore.hasRole(addr, ROLE_ADMIN)` for known candidate addresses
2. Read `DataStore` keys related to timelock configuration
3. Query Safe.getOwners() on the resolved multisig

This is exactly the kind of work the indexer is designed for. It's not a schema problem; it's a deployment-time data problem. Note this in the indexer spec.

## Recommendation

GMX exposed exactly the kind of governance variation the dashboard exists to surface. **Continue to Jupiter** — first Solana protocol, validates VM-agnostic claim. Solana's program upgrade authority model is fundamentally different from EVM's proxy admin pattern, and that's the next real test of the schema.

Expected from Jupiter:
- `controller_type: "program_authority"` exercised for the first time
- Squads V4 multisig (not Gnosis Safe) — schema enum `multisig.kind: "squads"` already supports this
- Possibly multiple programs under one Jupiter brand (perp, lend, dao) — exercises parent_protocol/market_id v0.2 fields properly

If Jupiter reveals fundamental issues with VM-agnostic modeling, we re-think before mapping Jito. If it works cleanly, the schema is genuinely VM-agnostic and we can ship.

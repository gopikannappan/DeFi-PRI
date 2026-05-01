# Curve Finance Mapping — Findings & Schema Observations

## What the mapping confirmed

**Schema generalizes again.** Curve's three-tiered Aragon DAO structure (Ownership/Parameter/Emergency) and immutable-pool-with-mutable-proxy architecture fit the existing schema with no field additions. The `controller_type: "dao"` with `dao.kind: "aragon"` works for all three agents, including the membership-token Emergency DAO that's structurally a multisig in DAO clothing.

**Curve's operational risk profile is different from Aave's, but not weaker.** This is an important dashboard point. Curve has:
- Immutable pool contracts (no implementation upgrade for existing pools — major positive)
- 3-day per-pool admin_actions_delay enforced in pool code, not by central governance — distributed enforcement
- 1-week DAO voting on top of that
- Emergency DAO can pause but proven cannot trap funds (validated in production during 2023 reentrancy hack)
- Three-way separation of admin powers, each with different bars to clear

A naive scoring model that just counts "number of admins" would penalize Curve for having three. That would be wrong — three roles with different scopes is *more* protective than one super-admin, not less.

## The single most important finding: kill_pool() does NOT trap funds

Verified from source code and the 2023 reentrancy postmortem. When the Curve Emergency DAO calls `kill_me(pool)`:

- **Disabled:** exchange, add_liquidity, remove_liquidity_one_coin, remove_liquidity_imbalance
- **Still works:** remove_liquidity (proportional withdrawal at current pool ratio)

This is a deliberate design choice. Funds are never trapped by emergency action, only trading and partial withdrawals.

This matters for scoring because it splits the `can_freeze_user_funds` field into two distinct meanings:
1. Can the admin halt protocol activity? (yes for both Curve and Aave)
2. Can the admin trap user funds? (no for either)

Both Curve and Aave score positively on (2), even though both can do (1). A protocol where pause = total freeze with no exit (some lending protocols, some bridges) scores worse on (2).

**Schema impact:** the existing `can_freeze_user_funds: bool` field is fine but I've been documenting *intent* in `_note` fields. Should formalize.

## Schema observations

### 1. Hybrid DAO/multisig pattern is real and worth surfacing

The Curve Emergency DAO is the textbook example: it's an Aragon DAO (full vote/proposal mechanics) but with a 9-member non-transferrable membership token, making it structurally a 5-of-9 multisig. Aave's Guardians use a different pattern (Gnosis Safe directly), but the *governance posture* is similar — small fixed group, fast emergency response.

For scoring, both should be in the same bucket. The schema captures the structure correctly via `controller_type: "dao"` + non-fungible `voting_token`. **Scoring layer needs to recognize this pattern** and treat it like a multisig with `threshold = quorum × member_count`.

Add to score input rubric: "if `dao.voting_token` is a non-transferrable membership NFT/token with <20 holders, treat as a multisig."

### 2. Time-bounded emergency capability is a positive signal worth surfacing

Older Curve pools have `kill_deadline` — kill_me() only callable for ~2 months after deployment, then the capability *expires*. After deadline, the pool becomes fully autonomous and not even the Emergency DAO can pause it.

This is a feature most protocols don't have and dashboards never highlight. **Score input addition:** if a protocol has *expiring* emergency capability, that's a strong positive signal worth points. New schema field idea (v0.2): `expires_at` or `is_time_bounded: bool` on emergency_controls entries.

### 3. Per-protocol delay constants embedded in core contracts

Curve enforces 3 days between commit_parameters and apply_parameters at the *pool contract* level (admin_actions_delay constant). This is enforced by the immutable pool code itself, not by a central timelock contract.

This is structurally different from Aave's Executor Lvl1 timelock, which is a separate contract that all calls flow through. Curve's pattern is *distributed* — every pool independently enforces its own delay. An attacker who somehow got control of the Aragon Ownership Agent still couldn't bypass per-pool delays because the constraint is in pool bytecode.

Schema currently captures this via `timelocks[].address: "pool-level"` with a note. Acceptable for now. **v0.2 candidate:** distinguish "centralized timelock" from "per-contract enforced delay" since they have different attack surfaces.

### 4. crvUSD as separate sub-system

Curve also operates crvUSD with its own admin surface (markets, controllers, peg keepers, monetary policy contracts). Treating "Curve" as one record loses this. Same problem we flagged for Aave (Main vs Prime vs Lido markets).

**Reinforces v0.2 decision:** separate slugs per market/sub-system. Curve mapping covers `curve` (AMM); a separate `curve-crvusd` record would cover the stablecoin system. Don't try to merge them.

## Cross-protocol observations from three mappings

We now have three protocols mapped: Uniswap V3, Aave V3, Curve. Patterns emerging:

| Pattern | Uniswap V3 | Aave V3 | Curve |
|---|---|---|---|
| Core implementation | Immutable | Upgradeable proxy | Immutable per-pool |
| Pause function | None | EMERGENCY_ADMIN (5/9 Safe) | Emergency DAO (9-member Aragon) |
| Pause traps funds | n/a | No | No |
| Timelock on changes | 2 days (single) | 1d Lvl1 / 7d Lvl2 | 1 week vote + 3 day per-pool |
| Governance form | Governor Bravo + Timelock | Aave Governance V3 (cross-chain) | Aragon dual-DAO + Emergency DAO |
| Top-3 risk score factors | Single timelock, no kill | Multi-tier delays | Distributed delays + immutable cores |

All three should score *high* on operational risk. The dashboard's value is mostly in catching the protocols that *don't* look like this — single-EOA admins, no timelock, no separation of emergency from ownership, mutable cores with no delay. Lido is next; will be interesting to see how it compares (Lido has had governance scrutiny in the past around oracle committees and validator exit signing).

## Score input refinement (running list)

Inputs to the scoring function as patterns confirm across protocols:

1. `min_timelock_delay` → `weighted_timelock_delay` (weight by blast radius)
2. `multisig_threshold_ratio` (m/n)
3. `multisig_signer_overlap_global` (signer in 3+ multisigs across protocols)
4. `emergency_can_trap_funds` (vs pause-only)
5. `core_implementation_immutable` (binary, strong positive)
6. `emergency_capability_expires` (time-bounded kill flag)
7. `admin_separation_score` (counts distinct roles with different controllers — *more* is better up to a point)
8. `distributed_delay_enforcement` (per-contract vs central timelock)

Scoring layer comes after we have 5–6 mapped protocols. Don't try to build it in advance.

## Schema decision tracker

Three v0.2 candidates now confirmed by 2+ protocols:

- **Multi-market split per protocol** (Aave: Main/Prime/Lido/EtherFi; Curve: AMM/crvUSD/Lending) — confirmed twice. **Lock for v0.2.**
- **`role_based.members[]` structure with member_type per holder** — Aave only so far. Wait for Lido.
- **Time-bounded emergency capability** — Curve only so far. Wait for one more.

Lido next, per tracker. Should lock down at least 2 of the 3 v0.2 candidates after that.

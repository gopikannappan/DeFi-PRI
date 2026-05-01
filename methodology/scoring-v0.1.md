# Protocol Risk Index — Scoring Methodology v0.1

## Design principles

1. **Transparent.** Every score input is a function of one or more observable schema fields. The function is published. There is no black box.
2. **Composable.** Each input produces a score in [0, 100] with documented weights. The composite is a weighted average. Anyone can reproduce the score from the schema record.
3. **Bounded.** No input dominates. No input is missing. Every protocol gets a value for every input — when data is missing, that absence is itself an input (uncertainty penalty).
4. **Conservative on uncertainty.** When a field is null or unverified, the input scores at the worse end of plausible values, not the better. We don't reward unknowns.
5. **Versioned.** The methodology has a version number. Score comparisons across versions require notation. v0.1 is current.

## Score categories

The composite score breaks into 5 categories, each weighted:

| Category | Weight | What it measures |
|---|---|---|
| **Governance Binding** | 20% | Are on-chain decisions actually constrained by token holders, or is it advisory? |
| **Time Buffer** | 25% | How much time exists between a malicious decision and irreversible execution? |
| **Authority Distribution** | 20% | How concentrated is the power to act maliciously? |
| **Emergency Design** | 15% | Quality of pause/kill mechanisms; can they trap funds? |
| **Code Mutability** | 20% | Can the core implementation be changed at all, and how? |

Total: 100%

## Per-input scoring functions

### 1. Governance Binding (20%)

Single categorical input. Maps directly to dashboard category.

| Pattern | Score | Examples |
|---|---|---|
| `immutable` (no governance possible) | 100 | (None mapped yet) |
| `token_bound_dao` (DAO vote binds on-chain action) | 85 | Uniswap V3, Aave V3, Curve, Lido |
| `hybrid` (some actions DAO-bound, others multisig) | 60 | Jupiter |
| `multisig_with_advisory_dao` (DAO is signaling only) | 45 | GMX V2 |
| `pure_multisig` (no DAO at all) | 30 | (None mapped yet) |
| `eoa` (single key) | 0 | (None mapped yet) |

Rationale: token-bound DAO scores high because compromising it requires compromising the token distribution, not just team members. Immutable scores higher still because no compromise is possible. Hybrid scores middle because partial protection is real but incomplete. Multisig + advisory DAO is more centralized than its branding suggests.

### 2. Time Buffer (25%)

Sum of weighted timelocks protecting different action classes. Score is a function of the *minimum* effective delay for the *most dangerous* action.

```
min_effective_delay_seconds = min(delay for any action that can drain or freeze funds)
```

| min_effective_delay | Score |
|---|---|
| ≥ 7 days | 100 |
| 3-7 days | 80 |
| 24-72 hours | 60 |
| 12-24 hours | 40 |
| 1-12 hours | 20 |
| < 1 hour or no timelock | 0 |

Bonus modifiers:
- **+10** if any timelock is *one-shot* (`is_one_shot: true`) — emergency capability that fires once and dies
- **+5** if any timelock is *time-expiring* (`expires_at: not null`)
- **+5** if delays are *tiered* by action severity (e.g. Aave Lvl1=1d, Lvl2=7d)
- **+5** if delay is *dynamic-extensible* by stakeholders (e.g. Lido Dual Governance)

Penalties:
- **-15** if *any* admin can bypass the timelock without unanimous consent (`can_bypass: true`)

Cap at 100, floor at 0.

### 3. Authority Distribution (20%)

Composite of three sub-inputs:

**3a. Multisig threshold ratio (50% of category)**

Take the most powerful multisig (highest blast radius). Score:

```
ratio = threshold / signer_count
```

| ratio | Score |
|---|---|
| ≥ 0.66 (e.g. 4/6, 5/7, 7/9) | 100 |
| 0.5-0.66 (e.g. 3/5, 4/7) | 75 |
| 0.4-0.5 | 50 |
| 0.33-0.4 (e.g. 2/5, 3/9) | 25 |
| < 0.33 or unknown threshold | 0 |

**3b. Role separation (30% of category)**

Count distinct admin roles with distinct controllers (different addresses):

| Distinct roles + controllers | Score |
|---|---|
| ≥ 5 | 100 |
| 3-4 | 75 |
| 2 | 50 |
| 1 | 25 |
| 0 (single super-admin) | 0 |

Rationale: Lido has 5+ distinct roles each with own controller. Aave has 7+ ACL roles. GMX has 4-5 keeper roles plus admin/timelock. Compromise of one role doesn't compromise all.

**3c. Cross-protocol signer overlap penalty (20% of category)**

Penalty if multisig signers also serve as signers for other top protocols. Computed at index time:

| Signer overlap | Score |
|---|---|
| 0 signers shared with other top-100 protocols | 100 |
| 1 signer shared | 75 |
| 2+ signers shared | 50 |
| Majority of signer set shared | 0 |

For static template scoring (no runtime data), default to 75 (assume some overlap is normal for established protocols).

### 4. Emergency Design (15%)

Composite:

**4a. Pause cannot trap funds (50% of category)**
- 100 if no pause exists (e.g. Uniswap)
- 100 if pause exists but does NOT trap funds (e.g. Curve kill_pool, Aave EMERGENCY_ADMIN, Lido stETH stop with withdrawal still possible)
- 50 if pause temporarily traps funds (e.g. Lido GateSeal — fixed duration freeze)
- 0 if pause permanently traps funds with no auto-resume

**4b. One-shot or time-bounded emergency (30% of category)**
- 100 if any emergency capability is `is_one_shot: true` or has `expires_at`
- 50 if some are limited but main emergency is unlimited
- 0 if all emergency authorities are perpetual

**4c. Pause requires multisig consensus (20% of category)**
- 100 if pause requires multisig threshold (m-of-n)
- 75 if pause requires DAO vote (slow but inclusive)
- 50 if asymmetric — single member can pause, group required to resume
- 25 if any single keeper can pause unilaterally
- 0 if pause is held by EOA

Note: Asymmetric pause (single can stop, many required to start) is sometimes a deliberate safety design (Lido DSM). It scores 50 not lower because the *direction* of asymmetry matters — easier to stop is safer for users than easier to resume.

### 5. Code Mutability (20%)

Single primary input on the most-critical contract:

| Mechanism | Base score |
|---|---|
| `immutable` | 100 |
| `program_upgrade` (Solana) with multisig auth, timelock, no DAO | 50 |
| `program_upgrade` (Solana) with multisig auth, no timelock | 30 |
| `transparent_proxy` / `eip1967_proxy` with timelock + DAO | 75 |
| `transparent_proxy` / `eip1967_proxy` with timelock only | 60 |
| `transparent_proxy` / `eip1967_proxy` with multisig only | 40 |
| `uups` with admin-only upgrade | 30 |
| Upgradeable via EOA | 0 |

Modifier:
- **+10** if upgrade requires DAO vote in addition to other gates
- **+5** if upgrade has been called fewer than 3 times in protocol history (track record signal)
- **-5** if upgrade authority is recoverable to less-secure setups (e.g. multisig can renounce timelock)

## Composite

```
score = 0.20 * governance_binding
      + 0.25 * time_buffer
      + 0.20 * authority_distribution
      + 0.15 * emergency_design
      + 0.20 * code_mutability
```

Round to nearest integer.

## Risk band

| Composite | Band |
|---|---|
| 85-100 | A — Mature governance, low operational risk |
| 70-84 | B — Solid governance with notable trade-offs |
| 55-69 | C — Functional but with material centralization or risk |
| 40-54 | D — Weak governance, significant trust assumptions |
| 0-39 | E — Centralized; trust is the team, not the code |

Bands are intentionally conservative — most top-100 protocols should score B or C. An "A" rating should be earned, not awarded.

## What this score does NOT measure

- **Code quality.** A protocol can have great governance and exploitable bugs.
- **Economic design.** Liquidity, liquidations, peg stability are out of scope.
- **Token distribution.** LDO concentration, voter turnout, etc. are downstream of governance design but not directly scored.
- **Off-chain trust surface.** Validator keys, oracle infrastructure, daemon software. Tracked separately as "trust_surface" notes; will be scored once the v0.3 schema field is added.
- **Track record.** Time-in-market and past incidents are tracked separately as protocol metadata, not scored.

The score is one signal among several. Users should read the full record, not just the number.

## Reproducibility

Anyone with a record's JSON can reproduce its score by:
1. Read methodology v0.1 (this document)
2. Apply each scoring function to the schema fields
3. Compute weighted composite
4. Compare to published score

If results differ by more than 1 point, file an issue. Scoring should be deterministic given the same schema record.

## Versioning

v0.1 — initial publication, 6 protocols mapped (Uniswap V3, Aave V3, Curve, Lido, GMX V2, Jupiter Aggregator).

Future versions:
- v0.2 expected when schema bumps to v0.3 with `governance_binding`, `trust_surface[]`, asymmetric multisig fields
- Methodology revisions require backwards-compatible scoring or explicit re-scoring of all protocols

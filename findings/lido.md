# Lido Mapping — Findings & Schema Observations

## What the mapping confirmed

**Schema generalizes — barely.** Lido is the deepest governance stack of any protocol mapped so far. Five layers of authority (Aragon Voting → Agent → Dual Governance → Admin Executor → protocol contracts), three independent committee-based emergency mechanisms (DSM guardians, GateSeal, Reseal), and meaningful operational trust surface that lives off-chain (validator keys, oracle infrastructure). The schema captured what's on-chain but the `_note` fields are doing more work than they should.

**Lido's risk profile is genuinely the most layered of the four protocols mapped.** Every key action has multiple checks:
- Routine ops: Easy Track + objection period + DG timelock
- Protocol changes: Aragon Vote + DG dynamic timelock (3-45+ days)
- Emergency: DSM guardian unilateral pause OR GateSeal one-shot OR Reseal extension
- stETH holders have built-in exit-or-veto power via DG escrow

This makes Lido relatively defensible compared to the broader staking landscape. The dashboard will need to articulate this clearly — Lido has had governance scrutiny historically (centralization concerns about LDO token concentration), but the *mechanism design* has matured significantly with Dual Governance live. We should reflect both the strong mechanism and the underlying token concentration honestly.

## Three new schema observations from Lido

### 1. Dynamic / extensible timelock is a new pattern

Dual Governance is a stakeholder-extensible timelock. "At its core, Dual Governance represents a dynamic timelock: the more exit signals stETH holders submit, the longer LDO-governance motions are delayed." Range: 3 days minimum → 45 days at 10% TVL locked → unbounded during Rage Quit.

Schema's current `delay_seconds: int` captures only one number. We're using minimum, but losing the ceiling and the extension trigger. **Schema v0.2 candidate:** add `delay_max_seconds` and `delay_extensible_by` (e.g., "stETH_lock", "vote", "guardian_signal") to timelock objects.

### 2. Asymmetric multisig threshold

DSM guardians have asymmetric authority: ANY 1 guardian can pause deposits, but ~2/3 quorum required to allow them. This is a deliberate safety design — fast defensive response, slow offensive action.

Schema's `multisig.threshold: int` is a single number. We're documenting the asymmetry in `_note` and via separate `emergency_controls` entries. Acceptable as workaround but lossy.

**Schema v0.2 candidate:** split `threshold` into `approve_threshold` and `pause_threshold` for committees with different authority levels per action. Or add an `actions[]` array on multisig with per-action thresholds. Defer until we see this pattern in EigenLayer (likely — EigenLayer's pauser-registry has similar semantics).

### 3. Off-chain trust surface needs first-class representation

Lido's actual operational risk includes:
- Validator signing keys held by node operators (off-chain)
- DSM daemon software running on guardian infrastructure
- Oracle committee beacon chain monitoring nodes

None of this is on-chain. None of it is in the schema. But all of it is real and material to user funds. The dashboard either:
(a) Says "we only track on-chain" and accepts losing this signal, or
(b) Adds a `trust_surface[]` field for known off-chain dependencies and indexes them by self-disclosure or research.

**Recommendation: (a) for v0.1.** Be explicit about what we track and what we don't. The `meta._out_of_scope_trust_surface` field on the Lido record is honest documentation of the gap. v0.2 can add structured `trust_surface[]` if there's clear demand. Don't try to be everything.

## Confirmed v0.2 candidates

### LOCK: Multi-market split per protocol (3rd confirmation)

Lido has Lido on Ethereum + Lido on L2s + (eventually) stVaults / V3 — these all have meaningfully different admin surfaces despite sharing the LDO governance token. Combined with Aave (Main/Prime/Lido/EtherFi) and Curve (AMM/crvUSD/Lending), this is now confirmed across 3 of 4 protocols mapped. **Lock for v0.2.**

### LOCK: Time-bounded one-shot emergency capability (2nd confirmation)

Curve has `kill_deadline` on older pools. Lido's GateSeal "fires once and dies." Same architectural pattern: emergency capability that expires after use. This is a *positive* signal for risk scoring (it's harder to abuse) and worth surfacing.

**Schema v0.2 field:** `emergency_controls[].is_one_shot: bool` and `emergency_controls[].expires_at: timestamp | null`. Lock for v0.2.

### Wait: `role_based.members[]` structure

Aave had it (RISK_ADMIN held by 5 different addresses). Lido has it implicitly (oracle committees, Easy Track factories). Curve doesn't really. Pattern is real but not universal yet. Wait for one more confirmation.

## Three new candidates from Lido (not yet locked)

1. **Dynamic timelock fields** (`delay_max_seconds`, `delay_extensible_by`) — only Lido so far
2. **Asymmetric multisig thresholds** (`approve_threshold` / `pause_threshold`) — only Lido so far; expecting EigenLayer to have similar
3. **Off-chain trust surface** (`trust_surface[]`) — Lido is the only protocol where this gap is glaring; LSTs and bridges will have similar issues. Defer.

## Pattern across four protocols

| Pattern | Uniswap V3 | Aave V3 | Curve | Lido |
|---|---|---|---|---|
| Core implementation | Immutable | Upgradeable proxy | Immutable per-pool | Upgradeable proxy |
| Timelock model | Single fixed (2d) | Tiered fixed (1d/7d) | Per-pool fixed (3d) + 1w vote | Dynamic 3-45+ days |
| Emergency model | None | Pause-only multisig | Multi-action DAO | Multi-layer (1-of-N pause + GateSeal + Reseal) |
| Pause traps funds | n/a | No | No | Temporarily yes (GateSeal); permanently no |
| Off-chain trust | None | None | Minimal | Significant (validator keys, daemon infra) |
| Token concentration risk | Mid | Mid | Low (vote-escrow) | Higher (LDO concentrated, mitigated by DG) |

The dashboard should articulate the Lido story honestly: governance mechanism is among the most sophisticated in DeFi, but the underlying LDO token distribution has historically been a centralization concern, and Dual Governance is a deliberate response to that concern. Both facts are true; the dashboard surfaces both.

## v0.2 schema decision: now is the right time

Four protocols mapped. Three locked candidates. We have enough confirmation to bump to v0.2 *before* mapping the remaining six protocols, rather than retrofitting later. Doing v0.2 now means:

1. Markets[] split: Curve splits into `curve` + `curve-crvusd`; Aave splits into `aave-v3-main` + `aave-v3-prime` + `aave-v3-lido` + `aave-v3-etherfi`; Lido eventually splits into `lido-l1` + `lido-csm` + future
2. `is_one_shot` and `expires_at` on emergency_controls
3. Don't lock other candidates yet; wait for EigenLayer / Pendle / Maker

**Decision needed before proceeding to GMX:** do we bump to v0.2 now, or keep going on v0.1 and re-do all five existing mappings later?

Recommendation: bump to v0.2 now. The migration is cheap (rename slugs, add two fields). Doing it after 10 mappings would be expensive.

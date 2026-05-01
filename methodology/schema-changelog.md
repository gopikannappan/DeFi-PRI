# Schema v0.2 — Migration Notes

## Decision context

After mapping four protocols (Uniswap V3, Aave V3, Curve, Lido) on schema v0.1, two patterns surfaced that warranted a schema bump *before* mapping the remaining six. Doing the migration after 10 mappings would mean retrofitting all of them and re-validating; doing it now means the next 6 are first-time-correct.

## Changes applied

### 1. Multi-market protocol split — `identity.parent_protocol` and `identity.market_id`

**Why.** Several protocols operate multiple distinct markets/sub-systems with separate admin surfaces under one brand:

- **Aave V3:** Main Market, Prime Market, Lido Market, EtherFi Market — each has its own ACL Manager, POOL_ADMIN holder, can have different emergency admins
- **Curve:** AMM (PoolProxy), crvUSD (separate controller stack), Lending markets — independent admin surfaces
- **Lido:** Lido on Ethereum, eventual stVaults / V3, Community Staking Module — different control planes

Treating these as a single record loses real signal: Prime Market could have weaker controls than Main Market and we'd never see it. Treating them as completely unrelated also loses information — they *are* governed by the same DAO.

**The fix.** Each market gets its own slug. Records reference a parent via `parent_protocol` and identify themselves within it via `market_id`. Single-market protocols leave both null.

```json
// aave-v3-prime
"identity": {
  "slug": "aave-v3-prime",
  "name": "Aave V3 Prime Market",
  "parent_protocol": "aave-v3",
  "market_id": "prime",
  ...
}
```

The dashboard can group records by `parent_protocol` for the brand view and surface them individually for the risk view.

### 2. One-shot / time-bounded emergency capability — `is_one_shot` and `expires_at`

**Why.** Two protocols mapped exhibit the same pattern: emergency capabilities that fire once and lose authority, or that expire after a fixed window:

- **Curve older pools:** `kill_me()` only callable before `kill_deadline` (typically 2 months post-deployment)
- **Lido GateSeal:** Pauses critical contracts for fixed duration, then the GateSeal contract loses authority and a new one must be deployed by the DAO

This is a *positive* security signal worth surfacing — emergency capability that cannot be repeatedly abused is structurally safer than perpetual emergency authority.

**The fix.** Two new fields on `emergency_controls[]`:

- `is_one_shot: bool` — true if the capability is consumed by a single use
- `expires_at: timestamp | null` — fixed expiry, null if non-expiring

These compose: a control can be both (Curve kill_deadline) or just one (GateSeal is one-shot but doesn't have a fixed expiry — it expires by being used).

### 3. Schema version bump

`meta.schema_version` moves from `"0.1"` to `"0.2"`. The schema `$id` URL also updates to `/v0.2.json`.

## What did NOT change

These were considered and explicitly deferred:

| Candidate | Status | Rationale |
|---|---|---|
| `dynamic_timelock` (delay_max_seconds, extensible_by) | Deferred | Only Lido Dual Governance exhibits this so far. Wait for one more confirmation. |
| `asymmetric_multisig_thresholds` (approve / pause split) | Deferred | Only Lido DSM exhibits this. EigenLayer pauser-registry will likely confirm. |
| `role_based.members[]` structure | Deferred | Aave shows it. Lido shows it implicitly. Curve doesn't. Wait for one more. |
| `trust_surface[]` for off-chain dependencies | Deferred | Lido is the only protocol where this gap is significant. Stay explicit-out-of-scope for now. |

If 2 of 4 deferred candidates get confirmed in the next 6 protocols, do v0.3 then. If only 1 of 4 confirms, leave them deferred.

## Migration semantics

The migration is **additive only**. No existing fields removed, no existing fields had their types changed in a breaking way. Any v0.1 record can be auto-upgraded to v0.2 by:

1. Adding `parent_protocol: null` and `market_id: null` to identity
2. Adding `is_one_shot: false` and `expires_at: null` to each emergency_control
3. Setting `meta.schema_version` to `"0.2"`
4. Special-casing known one-shot controls (Lido GateSeal/Reseal) to `is_one_shot: true`

The migration script `migrate_v01_to_v02.py` does exactly this. v0.1 backups are preserved as `*.v01.json.backup` for any regression check.

## What this means for the next 6 protocols

GMX, Jupiter, EigenLayer, Pendle, Jito, MakerDAO/Sky get mapped against v0.2 directly. EigenLayer in particular is likely to surface the asymmetric-multisig pattern (its pauser-registry has similar semantics to Lido's DSM). MakerDAO/Sky has many sub-systems and will exercise the parent_protocol/market_id split heavily.

If patterns continue to confirm, expect v0.3 around the 8th or 9th mapping. The cost of bumping schema versions early is small if migrations stay additive. The cost of leaving v0.1 in place across 10 mappings would have been compounding.

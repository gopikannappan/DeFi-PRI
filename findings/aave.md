# Aave V3 Mapping — Findings & Schema Observations

## What the mapping confirmed

**The schema generalizes.** Aave V3's structure — multi-role ACL, multi-tier executor timelocks, two distinct guardian multisigs, cross-chain governance — fit into the existing schema with zero structural changes. One small fix needed (allowing null in multisig.signers for template state); no new fields required.

**Aave's operational risk profile is genuinely strong.** This matters for the dashboard's credibility — when we score Aave high and a smaller protocol low, the score has to be defensible. Aave's structure: dual timelock executors (1d / 7d), separate emergency vs governance guardians (5/9 each, distinct signer sets), guardians can pause but not drain, and the 7-day Lvl2 timelock gates anything that touches token logic or governance parameters. This is what mature DeFi governance looks like. The dashboard should reflect that, not penalize them for being on-chain administrable.

## Schema observations

### 1. "One protocol, multiple markets" is unmodeled and matters

Aave on Ethereum has at least four separate Pool instances: Main Market, Prime (formerly Lido) Market, Lido Market, and EtherFi Market. Each has its own ACL Manager, its own POOL_ADMIN holder, and potentially different emergency admins. Treating "Aave V3" as a single record loses real signal — Prime Market could have a weaker admin setup than Main Market, and we'd never see it.

**Decision needed:** Do we model these as separate `slug`s (e.g. `aave-v3-main`, `aave-v3-prime`) or as a `markets[]` array within one Aave record? Recommendation: separate slugs. Each market has independent risk, deserves its own row in the dashboard, and Slicr/xTheo would query them independently. Treat the parent "Aave V3" as a category label, not a record.

This is a v0.2 concern — not blocking — but flag now.

### 2. `role_based` controller_type needs more structure than the schema currently gives it

I used `controller_type: "role_based"` for RISK_ADMIN and ASSET_LISTING_ADMIN with a free-text note saying "indexer enumerates at runtime." That works for now but loses fidelity. RISK_ADMIN being held by 5 different addresses (some of which are themselves multisigs, some EOAs, some smart contracts) is structurally important.

**Schema v0.2 should add:**
```yaml
role_based: {
  members: [{
    address: address,
    member_type: enum,        # eoa | multisig | timelock | contract
    risk_factor: float        # 0-1; computed at index time based on member_type
  }],
  member_count: int
}
```

Defer until we hit a second protocol that has the same pattern (Lido and EigenLayer probably will). If both confirm the need, add to v0.2.

### 3. Cross-chain governance needs first-class modeling, eventually

Aave V3 deployed on 12+ chains, all governed from Ethereum via PayloadsControllers and a.DI bridge. On Polygon, the POOL_ADMIN is the Polygon PayloadsController, which is controlled by Ethereum governance via cross-chain message. The current schema can express "controller is a contract on this chain" but doesn't capture the *cross-chain authority chain*.

For the MVP scoring, we can ignore this — score each chain's deployment independently. But for the dashboard story, "this admin on Polygon is actually controlled by Ethereum governance" is information users want.

**Schema v0.3 idea (not v0.2):** add `cross_chain_authority` field to controller, expressing the upstream chain + contract. Skip until at least 3 protocols expose this pattern.

### 4. Score input refinement: "delay_seconds" is the wrong granularity alone

Aave has effectively two delays: 1-day for routine changes, 7-day for governance/token changes. A naive score that takes "min delay = 1 day" misses that the *most dangerous* changes (token upgrades) are 7-day gated. Score should weight by *blast radius of what each delay protects*.

**Score input change:** instead of `min_timelock_delay`, use `weighted_timelock_delay` where weight = blast radius of protected actions. Implement after Curve mapping (Curve will have similar tiered delays).

### 5. `last_changed_block` is not enough — we want change-history

For the dashboard, "this multisig threshold was 4-of-7 last week and is now 2-of-7" is the high-signal alert. The current schema only stores the most recent change. The full history lives in indexer-side event logs, not in the schema record.

**Decision:** keep the schema as last-snapshot, store history in a separate event-log database that joins on protocol slug + role. The schema is the *current state*, the event log is the *change record*. Different storage characteristics, different access patterns.

## Landscape observations (relevant to product positioning)

### BGD Labs already publishes `aave-permissions-book`

This is a per-Aave permissions registry that tracks essentially what we're cataloging — for Aave alone. This is **good news**:

1. Confirms the demand for this kind of work exists at the protocol level
2. The output format is human-readable docs, not machine-readable data with diff alerts. Our Slicr/xTheo integration is genuinely additive.
3. We can use BGD's data as a reference / cross-validation source for Aave specifically. Don't re-derive what they've already documented; cite them.

If every top protocol had a BGD-quality permissions book maintained for them, the market for our dashboard would be smaller. They don't. Aave is the exception, not the norm.

### Implication for Curve next

Curve will have:
- DAO via Aragon (different from Governor Bravo — schema's `dao.kind: "aragon"` already covers it)
- Emergency multisig with kill_pool() power on individual pools — this is an `emergency_control` with `can_freeze_user_funds: true` and likely no timelock
- Per-pool admin separate from DAO admin
- Crypto-pools vs stable-pools have different admin surfaces

Curve will exercise `emergency_controls` more thoroughly than Aave did (Aave's emergency is pause-only, Curve's emergency can kill pools). That's why it's next in the order — to validate the emergency_controls modeling.

## Next-step decisions

Before mapping Curve, three small decisions to lock:

1. **Schema v0.2 trigger.** Mapping Aave revealed two enhancements (markets[] split, role_based.members structure). Don't bump yet — wait for Curve and Lido to confirm the patterns are general. If 3 of 5 EVM protocols demand the same change, do v0.2 then.

2. **Indexer populates which fields.** Confirm that the static template's `null` fields are exactly: `tvl_usd`, `as_of`, `last_changed_block`, `last_changed_tx`, `signers`, `signer_count`, `last_indexed_block`, `last_full_audit`, and per-protocol implementation addresses. Everything else should be set in the static record. This boundary determines how much manual work each protocol takes.

3. **Address verification process.** I used placeholder addresses for the two Guardian Safes. The Aave Protocol Guardian and Aave Governance Guardian addresses should be verified via the BGD aave-address-book before this record goes live. Not blocking the schema work, but blocking publication.

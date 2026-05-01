#!/usr/bin/env python3
"""
Compute v0.1 scores for all 10 mapped protocols.
Per scoring-methodology-v0.1.md.
"""

import json

WEIGHTS = {
    "governance_binding": 0.20,
    "time_buffer": 0.25,
    "authority_distribution": 0.20,
    "emergency_design": 0.15,
    "code_mutability": 0.20,
}


def band(score):
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    if score >= 40: return "D"
    return "E"


def band_label(b):
    return {
        "A": "Mature governance, low operational risk",
        "B": "Solid governance with notable trade-offs",
        "C": "Functional but with material centralization or risk",
        "D": "Weak governance, significant trust assumptions",
        "E": "Centralized; trust is the team, not the code",
    }[b]


# Original 6 protocols
uniswap = {
    "slug": "uniswap", "display_name": "Uniswap", "category": "DEX", "chain": "Ethereum",
    "governance_pattern": "token_bound_dao",
    "scores": {"governance_binding": 85, "time_buffer": 60, "authority_distribution": 85, "emergency_design": 100, "code_mutability": 100},
    "key_facts": [
        "Core contracts are immutable",
        "Governance changes only fee tiers and protocol fee setter",
        "2-day timelock on the only privileged actions",
        "No emergency controls exist"
    ],
    "verified": True,
}

aave = {
    "slug": "aave", "display_name": "Aave", "category": "Lending", "chain": "Ethereum",
    "governance_pattern": "token_bound_dao",
    "scores": {"governance_binding": 85, "time_buffer": 100, "authority_distribution": 83, "emergency_design": 45, "code_mutability": 85},
    "key_facts": [
        "Tiered 1d/7d executors — protocol upgrades take 7 days",
        "Two 5/9 Guardian multisigs (Protocol + Governance Emergency)",
        "ACL Manager with 7+ distinct privileged roles",
        "Pause stops withdrawals temporarily — partial fund trap during emergency"
    ],
    "verified": True,
}

curve = {
    "slug": "curve", "display_name": "Curve", "category": "DEX", "chain": "Ethereum",
    "governance_pattern": "token_bound_dao",
    "scores": {"governance_binding": 85, "time_buffer": 100, "authority_distribution": 75, "emergency_design": 85, "code_mutability": 100},
    "key_facts": [
        "Pools are immutable; only proxies/factories upgradeable",
        "Three Aragon Agents with separation of powers (Ownership/Parameter/Emergency)",
        "kill_pool() does NOT trap user funds — remove_liquidity always works",
        "~10-day effective delay (1-week vote + 3-day per-pool admin delay)"
    ],
    "verified": True,
}

lido = {
    "slug": "lido", "display_name": "Lido", "category": "LST", "chain": "Ethereum",
    "governance_pattern": "token_bound_dao",
    "scores": {"governance_binding": 85, "time_buffer": 100, "authority_distribution": 95, "emergency_design": 65, "code_mutability": 85},
    "key_facts": [
        "Dual Governance: 3-day minimum, dynamically extensible up to 45+ days",
        "GateSeal: one-shot 11-day pause, capability is consumed by single use",
        "DSM uses asymmetric thresholds: 1-of-N pause, ~2/3 to allow",
        "Significant off-chain trust surface (validator keys, daemon infra) not scored here"
    ],
    "verified": True,
}

gmx = {
    "slug": "gmx", "display_name": "GMX", "category": "Derivatives", "chain": "Arbitrum",
    "governance_pattern": "multisig_with_advisory_dao",
    "scores": {"governance_binding": 45, "time_buffer": 40, "authority_distribution": 83, "emergency_design": 70, "code_mutability": 60},
    "key_facts": [
        "VERIFIED: TWO Safes hold TIMELOCK_ADMIN role — 0x8D1d... (5-of-8) and 0x58F5... (4-of-6)",
        "VERIFIED: Three ROLE_ADMIN holders (most powerful role); structure of those addresses not yet characterized",
        "Snapshot voting is advisory only — actual on-chain authority is multisig",
        "Cross-multisig signer overlap: 0xeAA56005... appears in both TIMELOCK_ADMIN multisigs"
    ],
    "verified": True,
}

jupiter = {
    "slug": "jupiter", "display_name": "Jupiter Aggregator", "category": "DEX", "chain": "Solana",
    "governance_pattern": "hybrid",
    "scores": {"governance_binding": 60, "time_buffer": 0, "authority_distribution": 68, "emergency_design": 100, "code_mutability": 30},
    "key_facts": [
        "VERIFIED: Squads V3 multisig 4-of-7 (config 7ZyDFz...; vault PDA CvQZZ23q... = on-chain upgrade authority)",
        "JUP DAO governs treasury and launchpad — NOT program upgrades",
        "Squads V3 has no native timelock — confirmed instant upgrade capability",
        "Aggregator is stateless — actual blast radius limited (methodology v0.1 does not weight this)"
    ],
    "verified": True,
}

# 4 NEW protocols
eigenlayer = {
    "slug": "eigenlayer", "display_name": "EigenLayer", "category": "Restaking", "chain": "Ethereum",
    "governance_pattern": "multisig_only",
    "scores": {"governance_binding": 30, "time_buffer": 90, "authority_distribution": 90, "emergency_design": 35, "code_mutability": 65},
    "key_facts": [
        "VERIFIED via decoded role-grant txn: Operations Multisig (PROPOSER+CANCELLER), Protocol Council (PROPOSER+EXECUTOR), Community (TIMELOCK_ADMIN)",
        "VERIFIED: Primary timelock 10 days; bEIGEN timelock 24 days (tiered)",
        "Asymmetric pause via PauserRegistry: Pauser Multisig 1-of-9 to pause, Operations 3-of-6 to unpause",
        "Community Multisig 9-of-13 can replace timelock entirely in private-key-compromise scenarios"
    ],
    "verified": True,
}

pendle = {
    "slug": "pendle", "display_name": "Pendle", "category": "Yield", "chain": "Ethereum",
    "governance_pattern": "hybrid",
    "scores": {"governance_binding": 60, "time_buffer": 0, "authority_distribution": 75, "emergency_design": 100, "code_mutability": 40},
    "key_facts": [
        "Verified: Pendle owner Safe at 0x8119EC16F0573B7dAc7C0CB94EB504FB32456ee1, 3-of-5 (ratio 0.60)",
        "Hybrid: vePENDLE binds incentive direction; multisig binds protocol upgrades",
        "Pendle proxies do NOT use EIP-1967 standard slots — admin/impl pattern is custom",
        "Individual yield markets are immutable — existing positions cannot be retroactively altered"
    ],
    "verified": True,
}

jito = {
    "slug": "jito", "display_name": "Jito (JitoSOL + Network)", "category": "LST", "chain": "Solana",
    "governance_pattern": "hybrid",
    "scores": {"governance_binding": 60, "time_buffer": 0, "authority_distribution": 83, "emergency_design": 100, "code_mutability": 40},
    "key_facts": [
        "VERIFIED: SPL Stake Pool Program upgrade authority is Squads V3 6-of-10 multisig with 10 distinct signers",
        "Pool manager 5eosrve6... is program-controlled (PDA, not regular wallet) — specific program TBD",
        "JTO Realms DAO governs strategic decisions",
        "JitoSOL is non-custodial — withdrawals always possible directly through program"
    ],
    "verified": True,
}

sky = {
    "slug": "sky", "display_name": "Sky (formerly Maker)", "category": "Stablecoin", "chain": "Ethereum",
    "governance_pattern": "token_bound_dao",
    "scores": {"governance_binding": 85, "time_buffer": 60, "authority_distribution": 95, "emergency_design": 85, "code_mutability": 85},
    "key_facts": [
        "VERIFIED: Pause delay is 24h (86400s), not 30h as some 2024 governance docs stated",
        "VERIFIED: ESM trigger threshold = 2^256-1 (mathematically impossible to invoke)",
        "Most purely token-bound DAO of any protocol mapped — no multisig in critical upgrade path",
        "SubDAO architecture (Spark, Grove) with operational autonomy under main Sky governance"
    ],
    "verified": True,
}


def compute_composite(p):
    s = p["scores"]
    composite = sum(s[k] * WEIGHTS[k] for k in WEIGHTS)
    p["composite_score"] = round(composite)
    p["band"] = band(p["composite_score"])
    p["band_label"] = band_label(p["band"])
    return p


protocols = [compute_composite(p) for p in [
    uniswap, aave, curve, lido, gmx, jupiter, eigenlayer, pendle, jito, sky,
]]

protocols_sorted = sorted(protocols, key=lambda p: -p["composite_score"])

output = {
    "methodology_version": "v0.1",
    "schema_version": "v0.2",
    "category_weights": WEIGHTS,
    "category_labels": {
        "governance_binding": "Governance Binding",
        "time_buffer": "Time Buffer",
        "authority_distribution": "Authority Distribution",
        "emergency_design": "Emergency Design",
        "code_mutability": "Code Mutability",
    },
    "band_definitions": {
        "A": {"range": "85-100", "label": "Mature governance, low operational risk"},
        "B": {"range": "70-84", "label": "Solid governance with notable trade-offs"},
        "C": {"range": "55-69", "label": "Functional but with material centralization"},
        "D": {"range": "40-54", "label": "Weak governance, significant trust assumptions"},
        "E": {"range": "0-39", "label": "Centralized; trust is the team, not the code"},
    },
    "protocols": protocols_sorted,
}

with open("scores.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"{'Protocol':<35} {'Composite':>10} {'Band':>5} {'Pattern':>32}")
print("-" * 88)
for p in protocols_sorted:
    print(f"{p['display_name']:<35} {p['composite_score']:>10} {p['band']:>5} {p['governance_pattern']:>32}")

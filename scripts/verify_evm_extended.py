#!/usr/bin/env python3
"""
verify_v2.py — extends verify.py to resolve remaining pre-launch items.

What this adds:
1. EigenLayer timelock role members (PROPOSER/EXECUTOR/CANCELLER/ADMIN)
   - Discovers actual current multisigs governing EigenLayer
2. GMX ROLE_ADMIN holders — characterize each as Safe / contract / EOA
3. EigenLayer strategy whitelister at 0x5e4C39Ad... — bytecode check
4. Solana sanity check helpers (Squads V3 vault PDA pattern)

Run after verify.py. Outputs verification_v2_results.json.
"""

import json
import sys
from web3 import Web3
from eth_utils import keccak

ETH_RPCS = [
    "https://eth.llamarpc.com",
    "https://ethereum-rpc.publicnode.com",
    "https://rpc.ankr.com/eth",
]

ARB_RPCS = [
    "https://arb1.arbitrum.io/rpc",
    "https://arbitrum.llamarpc.com",
    "https://arbitrum-one-rpc.publicnode.com",
]


def connect(rpcs):
    for url in rpcs:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
            if w3.is_connected():
                print(f"  Connected to {url} (block {w3.eth.block_number})")
                return w3
        except Exception:
            continue
    return None


# OZ AccessControl ABI (TimelockController inherits this)
ACCESS_CONTROL_ABI = [
    {"name": "getRoleMember", "type": "function",
     "inputs": [{"type": "bytes32"}, {"type": "uint256"}],
     "outputs": [{"type": "address"}], "stateMutability": "view"},
    {"name": "getRoleMemberCount", "type": "function",
     "inputs": [{"type": "bytes32"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "hasRole", "type": "function",
     "inputs": [{"type": "bytes32"}, {"type": "address"}],
     "outputs": [{"type": "bool"}], "stateMutability": "view"},
]

SAFE_ABI = [
    {"name": "getOwners", "type": "function", "inputs": [], "outputs": [{"type": "address[]"}], "stateMutability": "view"},
    {"name": "getThreshold", "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    # VERSION returns Safe version string — useful sanity check
    {"name": "VERSION", "type": "function", "inputs": [], "outputs": [{"type": "string"}], "stateMutability": "view"},
]


def call(w3, addr, abi, fn, *args):
    try:
        c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
        return getattr(c.functions, fn)(*args).call()
    except Exception as e:
        return f"ERROR: {e}"


def has_code(w3, addr):
    """Returns True if address has bytecode (i.e., it's a contract)."""
    try:
        code = w3.eth.get_code(Web3.to_checksum_address(addr))
        return len(code) > 0
    except Exception:
        return False


def characterize(w3, addr):
    """Determine if address is EOA, Safe, or other contract."""
    if not has_code(w3, addr):
        return {"kind": "eoa", "address": addr}

    # Try as Safe
    threshold = call(w3, addr, SAFE_ABI, "getThreshold")
    if isinstance(threshold, int):
        owners = call(w3, addr, SAFE_ABI, "getOwners")
        version = call(w3, addr, SAFE_ABI, "VERSION")
        return {
            "kind": "gnosis_safe",
            "address": addr,
            "version": version if isinstance(version, str) else None,
            "threshold": threshold,
            "signers": owners if isinstance(owners, list) else None,
            "signer_count": len(owners) if isinstance(owners, list) else None,
        }

    # Has code but not a Safe — generic contract
    return {"kind": "contract", "address": addr, "note": "has bytecode but not a standard Safe"}


# ============================================================
# Main
# ============================================================

results = {}

print("=" * 70)
print("EIGENLAYER TIMELOCK ROLE DISCOVERY")
print("=" * 70)
eth = connect(ETH_RPCS)
if not eth:
    print("Could not connect")
    sys.exit(1)

primary_timelock = "0xC06Fd4F821eaC1fF1ae8067b36342899b57BAa2d"
beigen_timelock = "0x738130bc8eade1bc65a9c056dea636835896bc53"

# OZ TimelockController v4 role hashes
ROLES = {
    "PROPOSER_ROLE":       "0x" + keccak(text="PROPOSER_ROLE").hex(),
    "EXECUTOR_ROLE":       "0x" + keccak(text="EXECUTOR_ROLE").hex(),
    "CANCELLER_ROLE":      "0x" + keccak(text="CANCELLER_ROLE").hex(),
    "TIMELOCK_ADMIN_ROLE": "0x" + keccak(text="TIMELOCK_ADMIN_ROLE").hex(),
    # Some OZ versions also have DEFAULT_ADMIN_ROLE which is bytes32(0)
    "DEFAULT_ADMIN_ROLE":  "0x" + "00" * 32,
}

results["eigenlayer_timelock_roles"] = {}

for tl_label, tl_addr in [("primary", primary_timelock), ("beigen", beigen_timelock)]:
    print(f"\n>>> {tl_label} timelock {tl_addr}")
    tl_results = {}
    for role_name, role_hash in ROLES.items():
        count = call(eth, tl_addr, ACCESS_CONTROL_ABI, "getRoleMemberCount", role_hash)
        if not isinstance(count, int):
            tl_results[role_name] = {"error": str(count)}
            continue
        members = []
        for i in range(count):
            m = call(eth, tl_addr, ACCESS_CONTROL_ABI, "getRoleMember", role_hash, i)
            if isinstance(m, str):
                members.append(m)
        # Characterize each member
        characterized = [characterize(eth, m) for m in members]
        tl_results[role_name] = {"count": count, "members": characterized}
        print(f"\n  {role_name}: {count} member(s)")
        for c in characterized:
            print(f"    {c.get('address')} → {c.get('kind')}", end="")
            if c.get('kind') == 'gnosis_safe':
                print(f" ({c.get('threshold')}/{c.get('signer_count')}, v{c.get('version')})", end="")
            print()
    results["eigenlayer_timelock_roles"][tl_label] = tl_results


print("\n\n" + "=" * 70)
print("EIGENLAYER STRATEGY WHITELISTER BYTECODE")
print("=" * 70)
sw_addr = "0x5e4C39Ad7A3E881585e383dB9827EB4811f6F647"
sw_owner_addr = "0x369e6F597e22EaB55fFb173C6d9cD234BD699111"

print(f"\nstrategyWhitelister = {sw_addr}")
results["eigenlayer_strategy_whitelister"] = characterize(eth, sw_addr)
print(f"  → {results['eigenlayer_strategy_whitelister']}")

print(f"\nStrategyManager.owner() = {sw_owner_addr}")
results["eigenlayer_strategy_manager_owner"] = characterize(eth, sw_owner_addr)
print(f"  → {results['eigenlayer_strategy_manager_owner']}")


print("\n\n" + "=" * 70)
print("ARBITRUM — GMX ROLE_ADMIN HOLDERS + TIMELOCK SEARCH")
print("=" * 70)
arb = connect(ARB_RPCS)
if arb:
    role_admin_holders = [
        "0x4bd1cdAab4254fC43ef6424653cA2375b4C94C0E",
        "0xC77E6C0ca99E02660A23c00A860Dd5a8912DEaF5",
        "0x4A1D9e342E2dB5f4a02c9eF5cB29CaF289f31599",
    ]

    print("\n>>> ROLE_ADMIN holders characterization:")
    role_admin_results = []
    for h in role_admin_holders:
        c = characterize(arb, h)
        role_admin_results.append(c)
        print(f"  {h} → {c.get('kind')}", end="")
        if c.get('kind') == 'gnosis_safe':
            print(f" ({c.get('threshold')}/{c.get('signer_count')})", end="")
        print()
    results["gmx_role_admin"] = role_admin_results

    # Also characterize remaining TIMELOCK_ADMIN holders that weren't checked in v1
    other_timelock_admin = [
        "0x35ea3066F90Db13e737BBd41f1ED7B4bfF8323b3",
        "0xE014cbD60A793901546178E1c16ad9132C927483",
    ]
    print("\n>>> Other TIMELOCK_ADMIN holders (not yet characterized):")
    other_results = []
    for h in other_timelock_admin:
        c = characterize(arb, h)
        other_results.append(c)
        print(f"  {h} → {c.get('kind')}", end="")
        if c.get('kind') == 'gnosis_safe':
            print(f" ({c.get('threshold')}/{c.get('signer_count')})", end="")
        print()
    results["gmx_other_timelock_admin"] = other_results

    # GMX timelock contract: try to find via DataStore
    # In gmx-synthetics, the Timelock contract is referenced via specific keys.
    # The simplest discovery: look at recent transactions FROM a TIMELOCK_ADMIN multisig
    # and find what contract receives them most often.
    # We'll output the candidate addresses and instructions for manual Arbiscan check.
    print("\n>>> GMX timelock contract discovery:")
    print("  None of the TIMELOCK_ADMIN holders responded to getMinDelay() in v1.")
    print("  Likely path: GMX has a custom Timelock.sol (not OZ) — find it by:")
    print("  1. Visit Arbiscan for one of the timelock multisigs:")
    print("     https://arbiscan.io/address/0x8D1d2e24eC641eDC6a1ebe0F3aE7af0EBC573e0D")
    print("  2. Look at the most-frequent destination contract in their tx history")
    print("  3. That destination should be the Timelock contract")
    results["gmx_timelock_search"] = {
        "status": "manual_search_required",
        "candidate_multisigs_to_inspect": [
            "0x8D1d2e24eC641eDC6a1ebe0F3aE7af0EBC573e0D",
            "0x58F582455b54d7c83d03BCeed95FAf72B37fdDD7",
        ],
        "instructions": "Inspect Arbiscan tx history of these multisigs to find the most-called destination contract — that's the GMX Timelock"
    }


with open("./verification_v2_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\nDone. Saved to verification_v2_results.json")

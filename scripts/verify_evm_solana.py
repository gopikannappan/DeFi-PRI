#!/usr/bin/env python3
"""
Resolve verification gaps in PRI protocol JSONs by querying public RPCs.

For each TBD address or null field, attempt to resolve via on-chain reads.
Outputs verification_results.json with confirmed values and discrepancies.

Strategy:
- Use multiple public RPCs with fallback
- Read EIP-1967 proxy admin slots
- Call standard Safe (getOwners, getThreshold)
- Call standard OZ TimelockController (getMinDelay)
- Call GMX RoleStore with proper keccak256 role keys
"""

import json
import sys
from web3 import Web3
from eth_utils import keccak

# Public RPCs - try in order
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
    """Connect to first working RPC in list."""
    for url in rpcs:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
            if w3.is_connected():
                bn = w3.eth.block_number
                print(f"  Connected to {url} (block {bn})")
                return w3
        except Exception as e:
            print(f"  Failed {url}: {e}")
            continue
    return None


# Standard ABIs (minimal - just what we need)
SAFE_ABI = [
    {"name": "getOwners", "type": "function", "inputs": [], "outputs": [{"type": "address[]"}], "stateMutability": "view"},
    {"name": "getThreshold", "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
]

TIMELOCK_ABI = [
    {"name": "getMinDelay", "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
]

# EIP-1967 admin slot
EIP1967_ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
EIP1967_IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"


def safe_call(w3, addr, abi, fn, *args):
    """Call a contract function, return None on error."""
    try:
        c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
        result = getattr(c.functions, fn)(*args).call()
        return result
    except Exception as e:
        return f"ERROR: {e}"


def read_storage(w3, addr, slot):
    """Read raw storage slot, return as address."""
    try:
        raw = w3.eth.get_storage_at(Web3.to_checksum_address(addr), slot)
        # Last 20 bytes are the address
        addr_bytes = raw[-20:]
        return "0x" + addr_bytes.hex()
    except Exception as e:
        return f"ERROR: {e}"


def query_safe(w3, addr, label):
    """Get Safe owners and threshold."""
    print(f"\n{label} ({addr}):")
    threshold = safe_call(w3, addr, SAFE_ABI, "getThreshold")
    owners = safe_call(w3, addr, SAFE_ABI, "getOwners")
    print(f"  threshold: {threshold}")
    if isinstance(owners, list):
        print(f"  signers ({len(owners)}):")
        for o in owners:
            print(f"    - {o}")
    else:
        print(f"  signers: {owners}")
    return {"address": addr, "threshold": threshold, "signers": owners if isinstance(owners, list) else None,
            "signer_count": len(owners) if isinstance(owners, list) else None}


def query_timelock(w3, addr, label):
    """Get timelock min delay."""
    print(f"\n{label} ({addr}):")
    delay = safe_call(w3, addr, TIMELOCK_ABI, "getMinDelay")
    if isinstance(delay, int):
        days = delay / 86400
        hours = delay / 3600
        print(f"  delay: {delay} seconds = {days:.2f} days ({hours:.1f} hours)")
    else:
        print(f"  delay: {delay}")
    return {"address": addr, "delay_seconds": delay if isinstance(delay, int) else None}


def query_proxy(w3, addr, label):
    """Read EIP-1967 proxy admin and implementation."""
    print(f"\n{label} ({addr}):")
    admin = read_storage(w3, addr, EIP1967_ADMIN_SLOT)
    impl = read_storage(w3, addr, EIP1967_IMPL_SLOT)
    print(f"  admin: {admin}")
    print(f"  implementation: {impl}")
    return {"address": addr, "admin": admin, "implementation": impl}


# ============================================================
# Main verification flow
# ============================================================

results = {}

print("=" * 70)
print("ETHEREUM MAINNET")
print("=" * 70)
eth = connect(ETH_RPCS)
if not eth:
    print("Could not connect to Ethereum RPC")
    sys.exit(1)


# --------- PENDLE V2 ---------
print("\n\n>>> PENDLE V2")
results["pendle"] = {}

# Owner Safe (user-provided)
results["pendle"]["owner_safe"] = query_safe(eth, "0x8119EC16F0573B7dAc7C0CB94EB504FB32456ee1", "Pendle Owner Safe")

# Read Pendle Router proxy admin to find timelock or admin
# Pendle Router V4: 0x888888888889758F76e7103c6CbF23ABbF58F946
results["pendle"]["router_proxy"] = query_proxy(eth, "0x888888888889758F76e7103c6CbF23ABbF58F946", "Pendle Router V4")

# Pendle vePENDLE
results["pendle"]["vependle_proxy"] = query_proxy(eth, "0x4f30A9D41B80ecC5B94306AB4364951AE3170210", "vePENDLE")

# Pendle VotingController
results["pendle"]["voting_controller_proxy"] = query_proxy(eth, "0x44087E105137a5095c008AaB6a6530182821F2F0", "VotingController")


# --------- EIGENLAYER ---------
print("\n\n>>> EIGENLAYER")
results["eigenlayer"] = {}

# Verify all multisigs
results["eigenlayer"]["pauser_multisig"] = query_safe(eth, "0x1a051eF1524cbaEa57Ca04319ef93fE78903D5E6", "Pauser Multisig (expect 1/9)")
results["eigenlayer"]["operations_multisig"] = query_safe(eth, "0x8eD55c7640497Db15aC32c698c1a06E2E604d865", "Operations Multisig (expect 3/6)")
results["eigenlayer"]["protocol_council"] = query_safe(eth, "0x841B988aaEafce13b6456ff34015FBc42Aedb7e6", "Protocol Council (expect 3/5)")
results["eigenlayer"]["community_multisig"] = query_safe(eth, "0xC107547924C7D1d3E2d10eA8DF534BBfC5F373e6", "Community Multisig (expect 9/13)")

# Timelocks
results["eigenlayer"]["primary_timelock"] = query_timelock(eth, "0xC06Fd4F821eaC1fF1ae8067b36342899b57BAa2d", "Primary Timelock (expect 10 days)")
results["eigenlayer"]["beigen_timelock"] = query_timelock(eth, "0x738130bc8eade1bc65a9c056dea636835896bc53", "bEIGEN Timelock")


# --------- SKY / MAKERDAO ---------
print("\n\n>>> SKY / MAKERDAO")
results["sky"] = {}

# Pause proxy - canonical address from Chainlog: MCD_PAUSE_PROXY = 0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB
results["sky"]["pause_proxy"] = query_proxy(eth, "0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB", "MCD_PAUSE_PROXY")

# MCD_PAUSE itself: 0x146921e16c3f6cf6dDe54E6E64A4E0F2A2b3FbBb -- read its delay
# Actually MCD_PAUSE is the older ds-pause. Let me check storage.

# Chief contract
results["sky"]["chief"] = query_proxy(eth, "0x929d9A1435662357F54AdcF64DcEE4d6b867a6f9", "Chief V2 (Sky)")

# SKY token
results["sky"]["sky_token"] = query_proxy(eth, "0x56072C95FAA701256059aa122697B133aDEd9279", "SKY token")


print("\n" + "=" * 70)
print("ARBITRUM MAINNET")
print("=" * 70)
arb = connect(ARB_RPCS)
if not arb:
    print("Could not connect to Arbitrum RPC")
else:
    # --------- GMX V2 ---------
    print("\n\n>>> GMX V2 ON ARBITRUM")
    results["gmx_v2"] = {}

    # GMX RoleStore - hasRole(address, bytes32)
    # Need to use keccak256("ROLE_ADMIN") as bytes32
    role_admin_hash = "0x" + keccak(text="ROLE_ADMIN").hex()
    timelock_admin_hash = "0x" + keccak(text="TIMELOCK_ADMIN").hex()
    print(f"\n  ROLE_ADMIN hash: {role_admin_hash}")
    print(f"  TIMELOCK_ADMIN hash: {timelock_admin_hash}")

    # GMX RoleStore: getRoleMembers(bytes32 roleKey, uint256 start, uint256 end)
    GMX_ROLESTORE_ABI = [
        {"name": "getRoleMembers", "type": "function",
         "inputs": [{"type": "bytes32"}, {"type": "uint256"}, {"type": "uint256"}],
         "outputs": [{"type": "address[]"}], "stateMutability": "view"},
        {"name": "getRoleMemberCount", "type": "function",
         "inputs": [{"type": "bytes32"}],
         "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    ]

    rolestore = "0x3c3d99FD298f679DBC2CEcd132b4eC4d0F5e6e72"

    print("\n  ROLE_ADMIN holders:")
    count = safe_call(arb, rolestore, GMX_ROLESTORE_ABI, "getRoleMemberCount", role_admin_hash)
    print(f"    count: {count}")
    if isinstance(count, int) and count > 0:
        members = safe_call(arb, rolestore, GMX_ROLESTORE_ABI, "getRoleMembers", role_admin_hash, 0, count)
        if isinstance(members, list):
            for m in members:
                print(f"    - {m}")
        results["gmx_v2"]["role_admin"] = {"count": count, "members": members if isinstance(members, list) else None}

    print("\n  TIMELOCK_ADMIN holders:")
    count2 = safe_call(arb, rolestore, GMX_ROLESTORE_ABI, "getRoleMemberCount", timelock_admin_hash)
    print(f"    count: {count2}")
    if isinstance(count2, int) and count2 > 0:
        members2 = safe_call(arb, rolestore, GMX_ROLESTORE_ABI, "getRoleMembers", timelock_admin_hash, 0, count2)
        if isinstance(members2, list):
            for m in members2:
                print(f"    - {m}")
        results["gmx_v2"]["timelock_admin"] = {"count": count2, "members": members2 if isinstance(members2, list) else None}


# Save results
with open("./verification_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n" + "=" * 70)
print("Done. Results saved to verification_results.json")
print("=" * 70)

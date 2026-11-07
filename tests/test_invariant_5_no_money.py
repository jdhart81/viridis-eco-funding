"""Invariant 5 - No money movement anywhere in the codebase: no payment SDKs, private
keys, wallet code or token minting. This test greps the repository and fails on any hit.

Scope: every tracked text file except this test (which must name the patterns).
Prose files may *state the boundary* ("no wallets"), so prose gets a narrower scan for
key material and SDK names; code, configuration and dependency manifests get the full
pattern set.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

from conftest import ROOT

SELF = Path(__file__).resolve()
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist",
             ".ipynb_checkpoints", "htmlcov"}
SKIP_SUFFIXES = {".png", ".jpg", ".pdf", ".pyc", ".whl", ".gz", ".zip"}
SKIP_NAMES = {"LICENSE", ".coverage"}

PAYMENT_SDKS = [
    "stripe", "paypal", "braintree", "adyen", "square", "plaid", "dwolla", "wise", "coinbase",
    "web3", "eth_account", "eth-account", "ethers", "solana", "solders", "bitcoinlib", "bit",
    "pycoin", "monero", "algosdk", "xrpl", "stellar_sdk", "stellar-sdk", "brownie", "ape",
    "hdwallet", "bip_utils", "mnemonic", "pynacl", "nacl", "ecdsa", "coincurve", "secp256k1",
]
KEY_MATERIAL = [
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    r"\b0x[0-9a-fA-F]{64}\b",                     # raw 256-bit hex key
    r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{10,}",  # payment-processor secret keys
    r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b",      # WIF private keys
    r"\bxprv[1-9A-HJ-NP-Za-km-z]{100,}",          # extended private keys
]
CODE_PATTERNS = KEY_MATERIAL + [
    r"\bprivate[_ ]?key\b", r"\bprivkey\b", r"\bsecret[_ ]?key\b", r"\bseed[_ ]?phrase\b",
    r"\bwallet\w*\s*[=(]", r"\bWallet\w*\(", r"\bmint\w*\s*\(", r"\bERC-?(?:20|721|1155)\b",
    r"\bsend_?transaction\b", r"\bsign_?transaction\b", r"\btransfer(?:From)?\s*\(",
    r"\bpayout\w*\s*\(", r"\bcharge\w*\s*\(", r"\bPaymentIntent\b", r"\bcheckout\b",
    r"\bimport\s+(?:" + "|".join(re.escape(s) for s in PAYMENT_SDKS if s.isidentifier()) + r")\b",
    r"\bfrom\s+(?:" + "|".join(re.escape(s) for s in PAYMENT_SDKS if s.isidentifier()) + r")\b",
]
PROSE_PATTERNS = KEY_MATERIAL + [
    r"\bpip install\s+(?:" + "|".join(re.escape(s) for s in PAYMENT_SDKS) + r")\b",
]
CODE_SUFFIXES = {".py", ".toml", ".cfg", ".ini", ".json", ".yml", ".yaml", ".js", ".mjs",
                 ".ts", ".sh", ".ipynb", ".txt"}
PROSE_SUFFIXES = {".md", ".cff"}


def repo_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() == SELF:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        yield path


def test_scan_covers_the_code():
    names = {p.relative_to(ROOT).as_posix() for p in repo_files()}
    assert "src/viridis_eco_funding/pool/simulator.py" in names
    assert "src/viridis_eco_funding/mcp_server.py" in names
    assert "pyproject.toml" in names


def test_no_money_patterns_in_code_or_prose():
    hits = []
    for path in repo_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix in CODE_SUFFIXES or path.name in {"llms.txt", "NOTICE"}:
            patterns = CODE_PATTERNS if path.suffix != ".txt" or path.name == "llms.txt" else KEY_MATERIAL
        elif path.suffix in PROSE_SUFFIXES or path.suffix == "":
            patterns = PROSE_PATTERNS
        else:
            patterns = KEY_MATERIAL
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)!r}")
    assert not hits, "money-movement patterns found:\n" + "\n".join(hits)


def test_no_payment_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    deps = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        deps.extend(extra)
    names = {re.split(r"[<>=!~\[ ;]", d, maxsplit=1)[0].lower() for d in deps}
    assert names.isdisjoint({s.lower() for s in PAYMENT_SDKS}), names
    assert project.get("dependencies") == [], "the core must stay standard-library only"


def test_source_imports_are_stdlib_or_mcp():
    allowed_third_party = {"mcp", "uvicorn"}
    import sys
    stdlib = set(sys.stdlib_module_names)
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots = [node.module.split(".")[0]]
            else:
                continue
            for root in roots:
                assert root in stdlib or root in allowed_third_party or root == "viridis_eco_funding", \
                    f"{path.relative_to(ROOT)} imports {root}"
                if root in allowed_third_party:
                    assert path.name == "mcp_server.py", f"{path.name} must not import {root}"

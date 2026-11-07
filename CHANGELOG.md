# Changelog

## 0.1.0 (2026-11-07)

First working version (private repository).

- Valuation core `vef-method/0.1.0`: D-Score (MEE manuscript), power-law rarefaction for T, GSIP soil index (v0.1 convention), ECA over verified habitat with HDFM links, complexity score K = D* x ECA, and an intelligence-bound complexity-capacity term (conjecture) with compute parity.
- Sealed reproducible receipts (`vef-receipt/0.1`) and offline verification; read-only VergeCommon public-record binding.
- Pool schema `vef-pool/0.1` and an integer-exact simulator for milestone and outcome-linked releases.
- MCP server with five read-only tools over stdio and Streamable HTTP; `llms.txt` and `AGENTS.md`.
- Tests for all seven invariants, D-Score golden reproduction of Run 7, docs vocabulary checks and a method-version pin.
- Hardening after an independent adversarial review:
  - Determinism: every entry point pins the decimal context, and canonical formatting no longer depends on the caller's context. Magnitudes are kept inside the double range so receipts survive plain JSON. Strings are NFC-normalized.
  - Receipts: the receipt shape is exact; there is a top-level explanation; the seal kind is checked.
  - Pools: rules reward improvement only. Receipt-backed rules need `site_id` and `calendar`, and each receipt is single-use and bound to the period of its `observed_at`.
  - Labels: the explain label is derived from content, not from a caller-supplied flag.
  - Invariant 5 and 6 scanners: an AST scan of all Python, wider patterns, and mutation self-tests. A suite-wide socket guard blocks outbound connections.

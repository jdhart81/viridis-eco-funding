# Mounting viridis-eco-funding in the Viridis agent gateway

Target: `https://mcp.viridisconservation.com/eco-funding/mcp`, served by the gateway in `jdhart81/viridis-fleet-service` (`deploy/gateway/viridis_mcp_gateway.py`, `mcp==1.28.1`).

The agent side is done and tested in this repository. `tests/test_fleet_admission.py` checks AA1–AA4 and AA7, and `deploy/fleet/gateway_check.py` emulates the mount under `mcp==1.28.1` and under mcp 2.x. The edits below go into the gateway repository, in one commit, before deploy.

## 0. Vendor the agent

Copy this repository, without `.git`, to `viridis-eco-funding/` at the gateway repository root. The adapter is `viridis-eco-funding/adapters/mcp_server.py`. It defines module-level `mcp` (FastMCP) and `agent` (`describe()`, `health()`, `async process()`). It imports only the standard-library package in `src/viridis_eco_funding`, so it adds no pip dependencies to `requirements.lock`.

## 1. Mount and discovery (AA1)

In `deploy/gateway/viridis_mcp_gateway.py`:

```python
# MOUNTS
    "eco-funding":      "viridis-eco-funding",

# AGENT_SEO
    "eco-funding": {
        "desc": "Ecological complexity valuation for agents: D-Score x verified connected habitat -> sealed, re-runnable receipts, plus pledge-pool release simulation. Read-only, free rail; intelligence-bound term labelled conjecture.",
        "queries": [
            "value the biodiversity and habitat connectivity of a conservation site",
            "verify a reproducible ecological valuation receipt",
            "simulate milestone and outcome-linked releases for a conservation pledge pool",
            "D-Score biodiversity index for a woodland or hedgerow project",
        ],
    },

# catalog metadata block (next to "ghg-ledger")
    "eco-funding": {
        "name": "Viridis Eco-Funding",
        "category": "ecological-valuation",
        "tags": ["biodiversity", "d-score", "habitat-connectivity", "receipts", "conservation-funding"],
    },
```

Add the module docstring line `https://<host>/eco-funding/mcp       viridis-eco-funding`.

## 2. Economic decision (AA2): free rail

Do **not** add it to `PRICE_MINOR`. In `deploy/gateway/test_admission_invariants.py`, add it to `FREE_RAILS`:

```python
    "eco-funding":    "verification is the network effect: free re-runnable receipts are shared trust references",
```

This is free by doctrine, for the same reason verification is free across the fleet. It must also stay free because this agent's Invariant 5 rules out money movement. It is never gated, metered for payment, or wired to escrow.

## 3. Revenue model on record (AA3)

`viridis-eco-funding/agent.yaml` already carries `revenue_model` and `thesis_connection`.

## 4. Network edges (AA4)

Success envelopes teach these edges:
- `value_site` → `notary.commit` (timestamp the receipt seal; digests only), `regulatory-radar.build_evidence_pack`, `ghg-ledger.calculate_inventory`, `eco-funding.verify_receipt`, `eco-funding.simulate_pool`
- `verify_receipt` → `notary.verify`, `eco-funding.simulate_pool`

There are deliberately no edges to escrow, settlement or payments. Pools are modelled only, and any real pool needs legal review before money moves.

## 5. Shipping surfaces (AA5)

- `deploy/gateway/Dockerfile`: `COPY viridis-eco-funding/ viridis-eco-funding/`, next to the other agent COPY lines.
- `deploy/gateway/deck.html`, `const ROLE = {...}`: `"eco-funding": "ecological valuation"`.
- `deploy/glama/fleet_bridge.py`, ROLE: `"eco-funding": "ecological valuation"`.
- `deploy/glama/fleet_manifest.json`: regenerate with `scripts/generate_live_glama_manifest.py`, or paste `deploy/fleet/tools.json` → `tools`.
- Re-baseline the count-pinned release tests in the same commit (mounts 28 → 29).

## 6. Distribution (AA6), after the live health check passes

1. Public repository: `https://github.com/jdhart81/viridis-eco-funding`.
2. Official registry: `mcp-publisher validate deploy/fleet/server.json && mcp-publisher publish deploy/fleet/server.json` (owner account, `io.github.jdhart81` namespace).
3. Glama: Sync → Build & Release. Smithery: per-agent listing (Save Settings needs two clicks).

## 7. Quickstart (AA7)

Add `deploy/fleet/QUICKSTART_SNIPPET.md` to `docs/QUICKSTART_FIRST_CALL.md`.

## Verify after deploy

```bash
curl -s https://mcp.viridisconservation.com/health | jq '.agents["eco-funding"]'
python deploy/fleet/gateway_check.py   # local emulation; the live call is in QUICKSTART_SNIPPET.md
```

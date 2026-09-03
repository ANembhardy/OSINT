# rcwatch — Russia–China political coordination, tracked reproducibly

An OSINT workbench for one question: **how much of the Russia–China relationship
is actual coordination, and how much is alignment that would have happened
anyway?**

It exists because the usual way of answering — searching, reading commentary,
writing it up — produces claims that cannot be re-checked six months later. This
repo replaces that with addressable sources, a fixed set of measures, and a
provenance trail on every row of data.

## Layout

```
docs/01-methodology.md        measures M1-M6, and what each can and cannot establish
docs/02-source-inventory.md   every structured source: endpoint, format, tier, cadence
docs/03-findings-2026-09.md   first-pass substantive findings
docs/04-runbook.md            step-by-step collection
data/seed/                    hand-coded tables (contacts, joint documents, UNSC actions)
data/schema/                  JSON Schema for each table
src/rcwatch/                  library + CLI (stdlib only, no dependencies)
tests/                        offline test suite
```

## Quick start

No dependencies beyond Python 3.11 and `pytest` for the tests.

```bash
make test        # offline suite
make audit       # what in the seed data still lacks a primary record
make contacts    # leader-level contact indicators
make sql         # BigQuery SQL for the GDELT contact series
```

Live collection (needs unrestricted network):

```bash
PYTHONPATH=src python3 -m rcwatch undl \
    --query '"Ukraine"' --limit 50 --out out/votes_2025.csv

PYTHONPATH=src python3 -m rcwatch agreement \
    --votes out/votes_2025.csv --contested --baselines
```

## The one idea worth taking away

Vote agreement is the weakest available evidence of coordination and the most
widely cited. The evidence hierarchy this repo works to, strongest first:

1. co-signed documents carrying a UN symbol (joint letters to the Secretary-General)
2. co-penholding and co-sponsorship of draft resolutions
3. joint military activity under a standing annual plan
4. formulation adoption with a measurable lead-lag
5. sequenced vetoes and explanations of vote
6. simple vote agreement

Most published commentary on this dyad runs on (6) and reads as though it were (1).
Every claim produced here is tagged with its tier.

## Data conventions

- Vote coding follows Voeten: `1` yes, `2` abstain, `3` no, `8` absent, `9` not a member.
- Every seed row carries `source_url` and a `verification` status
  (`verified` / `pending_primary` / `low_confidence_date` / `disputed`).
  `make audit` reports what is outstanding. Rows marked `verified` are required
  by the test suite to carry a source.
- Fetches cache to `out/cache/` with a `.meta.json` sidecar recording URL and
  retrieval time.

## Status

First pass. The findings document is preliminary and says so: it was assembled
under a sandbox that blocked direct access to the UN, Kremlin and PRC MFA
domains, so tier-1 records are catalogued but not yet retrieved. Priorities for
the next pass are listed at the end of `docs/03-findings-2026-09.md`.

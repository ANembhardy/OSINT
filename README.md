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
make test        # offline suite (34 tests)
make ga          # Russia-China General Assembly voting analysis
make unsc        # Russia-China Security Council voting analysis
make ga-window   # the same, restricted to 2021-2026
make unsc-window #
make audit       # what in the seed data still lacks a primary record
make contacts    # leader-level contact indicators
make sql         # BigQuery SQL for the GDELT contact series
```

Two official UN voting datasets ship with the repo under `data/raw/`:
the Dag Hammarskjold Library General Assembly export (947k rows, 1946 to
Dec 2025) and the UNDL Security Council export (41k rows, 1946 to Jan 2026).
Both are UN copyright, non-commercial use with attribution.

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

Any window: `python -m rcwatch ga --since 2021-01-01 --until 2026-01-01`.

## What the data says

Results from the committed datasets, each reproducible and test-guarded.
Full series (1992-2025/26):

1. **The base rate inverts the headline.** On contested General Assembly votes
   1992-2025, Russia-China agreement is 58.4% -- *below* the Global South mean
   pairwise of 82.2%, and below China-India (78.2%) and China-Pakistan (83.3%).
   Russia is the isolate; China votes like a mainstream Global South member.
2. **The published "77% to 67% decline" is mostly a subsetting artefact.** It
   reproduces on the raw series (77.9% to 66.7%, 2018-2024) and nearly vanishes
   on contested votes (66.7% to 64.9%).
3. **Alignment is issue-contingent, sharply.** Emergency special session ES-10
   (Palestine): 92.3% agreement. ES-11 (Ukraine): 22.2%. China joined Russia in
   voting no on exactly two of nine Ukraine texts -- the Human Rights Council
   suspension and the reparations mechanism -- both precedent-setting rather than
   condemnatory.

Restricted to **2021-2026** (see `docs/03-findings-2026-09.md` section 1.6), the
dyad is *tighter*, not looser: contested GA agreement rises to 68.1% and Council
agreement to 63.6%. The base-rate inversion survives -- the Global South mean is
still higher at 79.3%. Two things drive the apparent convergence: China-India
fell 11 points while Russia-China rose 10, and US-Russia Council agreement
collapsed to 16.9%. Within the window Russia takes the more negative position in
95 of 101 contested GA splits, and abstains on 81% of contested Council
resolutions against China's 55%.

## Status

Section 1 of the findings is computed from primary data. Sections 2-4 (joint
statements, diplomatic contact, shared positions) are still assembled from
search retrieval, because the build sandbox blocked direct access to the UN,
Kremlin and PRC MFA domains. Priorities for the next pass are listed at the end
of `docs/03-findings-2026-09.md`.

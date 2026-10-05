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
docs/05-realism-lawfare-literature.md
                              annotated literature map: modern realism +
                              Russian lawfare (theory, four arenas, designs)
docs/06-thesis-design.md     which theories carry the lawfare thesis, and
                              where the design is exposed
docs/07-what-the-theory-does.md
                              plain-language: what theory is for in the
                              lawfare thesis, and the three jobs it does
docs/08-mechanisms-and-theory.md
                              maps the draft article's two mechanisms onto
                              political science theory
docs/09-phd-workplan.md       four-year plan and schedule, Feb 2026 start
docs/09-phd-workplan-lv.md    the same plan in Latvian (source for the .docx)
docs/10-russia-africa-summit-2026.md
                              pre-summit brief: third Russia-Africa Summit,
                              statements, participants, IOs
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

## Two measures, always reported together

- **exact** — identical votes / comparable votes
- **S-score** (Lijphart) — identical + 0.5 x partial split, over comparable votes

A partial split (one votes yes or no, the other abstains) is **partial
alignment**, not disagreement. In the Security Council this matters most: a
permanent member's "no" is a veto, so **Russia vetoing while China abstains is
partial alignment** -- the draft dies either way and China has denied it the
weight of a Council united but for Russia. Only a veto met by the other's *yes*
would be a real break, and that has never happened.

The gap between the measures is large: on the nine Ukraine emergency special
session texts the pair scores 22.2% exact and 61.1% graded. Baselines are always
computed on the same measure as the focus dyad.

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
3. **Alignment is issue-contingent.** ES-10 (Palestine): 96.2% graded. ES-11
   (Ukraine): 61.1% graded, 22.2% exact. **China never joined the Assembly
   majority on any of the nine Ukraine texts** -- but nor did 28 other states,
   India included, so abstention is weak evidence of coordination. What is rare
   is opposition: only 16 states voted no on two or more ES-11 texts, and China
   is the only major economy on that list besides Russia. Its two no votes were
   the Human Rights Council suspension and the reparations mechanism -- both
   precedent-setting rather than condemnatory.

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

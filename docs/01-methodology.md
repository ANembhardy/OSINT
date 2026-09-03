# Methodology

## The central problem: alignment ≠ coordination

Two states can vote identically at the UN for three quite different reasons:

1. **Coordination** — they consulted and agreed a common line in advance.
2. **Convergence** — they independently hold the same interest.
3. **Bloc effect** — both are voting with a larger caucus (G77, NAM, "Global South")
   and the dyadic match is incidental.

Almost all public reporting on Russia–China conflates these. An investigation is
only worth doing if it separates them, so every measure in this repo is tagged
with what it can and cannot establish. See the evidence ranking at the end of
`02-source-inventory.md`.

## Measures

### M1 — Dyadic vote agreement (contested subset)

For UNGA roll-calls in session *s*:

```
agreement(A,B) = ( identical_votes ) / ( votes where both A and B were present )
```

Report three variants, always together:

- **raw** — all roll-calls;
- **contested** — roll-calls where the minority side held ≥10% of votes cast;
- **important** — the State Department's "important votes" subset, or a topic filter.

The gap between raw and contested is itself a finding. Published figures for this
dyad (e.g. a fall from ~77% to ~67% between 2018 and 2024) are sensitive to which
variant is used, so reproducing them requires stating the variant.

### M2 — Base-rate controls

Never report M1 for Russia–China alone. Compute the same statistic for a control
set in the same sessions: Russia–India, China–India, China–Brazil, Russia–Iran,
China–Pakistan, plus the mean pairwise agreement across the G77. If Russia–China
agreement is 67% and the G77 internal mean is 71%, the "alignment" headline
inverts. This single control is the difference between analysis and vibes.

### M3 — Divergence typology

Classify every non-identical vote:

| Type | A | B | Reading |
|---|---|---|---|
| `partial_split` | Yes/No | Abstain | Hedging; one side declines to spend the capital |
| `opposed` | Yes | No | Genuine policy conflict |
| `absence` | vote | absent | Usually procedural, low signal |

A rise in `opposed` is a much stronger signal of divergence than a rise in
`partial_split`. In the Security Council the distinction is absolute: across
2,038 adopted resolutions since 1992, Russia and China have **never** voted on
opposite sides — every divergence is a partial split. Reported alignment declines in this dyad have been driven partly
by real opposed votes (death-penalty moratorium, humanitarian arms control such
as cluster munitions and landmines) — issues where the divergence reflects
domestic legal policy, not geopolitics. **Weight divergences by whether they
touch the dyad's shared strategic agenda.** A split on the death penalty says
almost nothing about strategic coordination; a split on a Ukraine or Middle East
text says a great deal.

### M4 — Security Council behaviour

Vetoes are rare, so treat them as a case list rather than a statistic
(`data/seed/unsc_vetoes.csv`). The richer signals are:

- **Joint vs. solo vetoes** — China's post-2005 vetoes have overwhelmingly come
  alongside Russia rather than alone. A solo Chinese veto would be a notable break.
- **Abstention divergence** — where Russia vetoes and China abstains (as on
  several Ukraine-related texts), which is the standard shape of Chinese hedging.
- **Penholdership and blocked drafts** — texts that never reach a vote because
  one or both signalled a veto in consultations. Sourced from Security Council
  Report, not from the voting record.

### M5 — Contact intensity

From the event table (`data/seed/meetings.csv`, schema in `data/schema/`):
count contacts per year **by level and by venue type**, distinguishing dedicated
bilateral visits from pull-asides at multilateral summits. Cross-validate the
hand-coded count against GDELT CAMEO `04`/`05` event volume for the RUS–CHN dyad.
Divergence between the two series is informative: hand-coded counts capture
significance, GDELT captures tempo including working-level contact.

Useful derived indicators:
- **reciprocity** — ratio of Moscow-hosted to Beijing-hosted meetings;
- **anniversary loading** — how much of the calendar is driven by commemorative
  dates (Victory Day, treaty anniversaries) versus substantive business;
- **document yield** — signed documents per leader meeting, as a crude measure of
  whether summits are producing or merely performing.

### M6 — Formulation tracking

Fixed marker-phrase dictionary (listed in `02-source-inventory.md` §5) counted
per speaker per year across UN verbatim records and MFA statements. Look for
**lead-lag**: which side introduces a formulation, and how long until the other
adopts it. Consistent one-directional adoption is evidence about who sets the
agenda within the partnership — a question that vote counting cannot touch.

## Standing cautions

- **Mirror-imaging the partnership.** The relationship is asymmetric and the
  asymmetry is growing. Treat "Russia and China both X" claims sceptically; check
  whether the two are doing X for the same reason and at the same cost.
- **Source contamination.** TASS, Xinhua, RT, Global Times and CGTN are state
  outlets and are legitimate *primary* sources for what a government wants said —
  and unreliable *secondary* sources for what happened. Tag them accordingly in
  citations rather than excluding them.
- **Absence of evidence.** Coordination that works is invisible. The lack of a
  joint statement on a topic is weak evidence of non-coordination.
- **Publication lag.** Voeten and ICEWS lag ~1 year; UNDL is near-current. Do not
  mix a 2024-vintage alignment score with a 2026 narrative without saying so.
- **Provenance discipline.** Every claim in an output file carries a source URL
  and a retrieval date. Findings sourced only to a search-engine summary are
  marked `unverified` until a primary record is attached.

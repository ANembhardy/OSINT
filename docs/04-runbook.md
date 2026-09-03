# Collection runbook

## A. UNGA alignment series

1. **Historical base.** Download the Voeten UNGA voting dataset from Harvard
   Dataverse (`doi:10.7910/DVN/LEJUQZ`). Reshape to the long format
   `rcid,session,country,vote`.
2. **Current tail.** Voeten lags roughly a year. Extend with UNDL:
   ```bash
   PYTHONPATH=src python3 -m rcwatch undl --query 'A/RES/80' --limit 200 --out out/votes_s80.csv
   ```
   UNDL returns MARCXML when `of=xm` is set; field **967** carries the per-country
   vote line. Country names, not ISO codes — build a crosswalk once and keep it.
3. **Score, three ways, with baselines:**
   ```bash
   PYTHONPATH=src python3 -m rcwatch agreement --votes out/votes_s80.csv --baselines
   PYTHONPATH=src python3 -m rcwatch agreement --votes out/votes_s80.csv --contested --baselines
   ```
4. **Sanity-check** the result against the State Department's annual *Voting
   Practices in the United Nations* coincidence tables. If your number is far off
   theirs, you have a subsetting or presence-handling bug, not a finding.

## B. Security Council

The universe is small enough to maintain by hand. Watch:

- the UN's veto page and the Dag Hammarskjöld Library veto table for new entries;
- `press.un.org` meeting coverage for **explanations of vote** — the text you need
  for formulation analysis;
- Security Council Report's Monthly Forecast for **penholdership and drafts that
  never reached a vote**, which is where the coordination that matters actually
  happens.

Append to `data/seed/unsc_actions.csv`, tagging `alignment` as
`joint` / `divergent` / `partial`.

## C. Joint documents

- **Standing UNDL query** for letters from the Permanent Representatives of China
  and the Russian Federation to the Secretary-General. Each hit is a tier-1
  coordination artifact with a permanent symbol. Record both `date_signed` and
  `date_circulated` — the gap is informative.
- **Trilingual diff.** For each major joint statement, retrieve the Russian
  (kremlin.ru), Chinese (fmprc.gov.cn) and English editions, align by paragraph,
  and diff. The three texts are negotiated, not translated; divergences mark
  clauses one side declined to commit to in its own language.

## D. Contact table

- Hand-code leader and FM level from the Kremlin's presidential schedule and the
  PRC MFA activities pages. The universe is ~5–8 leader meetings a year, so this
  is an afternoon's work and it is worth doing properly.
- Record `venue_type` honestly: a state visit and a 40-minute pull-aside on summit
  margins are different signals and press coverage flattens them.
- Cross-validate tempo against GDELT:
  ```bash
  make sql > out/contacts.sql   # then run against gdelt-bq.gdeltv2.events
  ```
  Deduplicate — GDELT emits one row per source article, so raw counts measure
  press attention as much as diplomacy.

## E. Formulation tracking

- Corpus: UN verbatim records (`A/../PV..`, `S/PV..`) via UNDL, plus the UN General
  Debate Corpus for the annual speeches, plus MFA statements.
- Run `rcwatch.phrases.count` per document; aggregate per speaker per year.
- Run `rcwatch.phrases.lead_lag` per marker to see who introduces vocabulary first.
- **Keep the dictionary frozen.** Changing it silently changes every historical
  number.

## F. Hygiene

- Never mark a row `verified` without a `source_url`; the test suite enforces this.
- Re-run `make audit` before quoting any aggregate.
- Note retrieval dates. State media (TASS, Xinhua, RT, Global Times, CGTN) are
  legitimate primary sources for what a government wants said and unreliable
  secondary sources for what happened — tag, do not exclude.

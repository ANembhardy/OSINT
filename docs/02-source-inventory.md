# Structured source inventory

The point of this file: replace ad-hoc searching with **addressable, re-pullable,
citable** sources. Every row below has a stable identifier scheme, a machine
format, and a refresh cadence, so a claim in a report can be traced back to a
specific record and the same query can be re-run six months later.

Legend for **Tier**:
- **A** — primary, machine-readable, versioned. Use for anything quantitative.
- **B** — primary but semi-structured (HTML/RSS). Needs a parser; still citable.
- **C** — secondary analysis. Use for framing and cross-checks, never as the sole basis for a number.

---

## 1. UN voting — General Assembly

| Source | Tier | Access | Notes |
|---|---|---|---|
| **UN Dag Hammarskjold Library, GA Voting Data** (UNDL record `4060887`) | A | Bulk CSV, versioned | **Use this first.** The publisher's own dataset: 947,434 rows, resolution 1 (1946) to 80/246 (Dec 2025), version 5 published Feb 2026. Currency beats Voeten by roughly a year. Held here as `data/raw/2026_02_06_ga_voting.csv.gz`; codebook mirrored at `docs/reference/ga_voting_codebook_v5.md`. Non-commercial use with attribution — cite as `rcwatch.ga.CITATION`. |
| **Voeten UNGA Voting Data** (Harvard Dataverse, `doi:10.7910/DVN/LEJUQZ`) | A | Dataverse API / bulk `.tab`, `.dta` | Still worth having for the **ideal-point estimates**, which the DHL export does not provide, and for continuity with the published literature. Lags ~1 year, so use DHL for the recent tail. |
| **UN Digital Library (UNDL)** `digitallibrary.un.org` | A | REST search + MARCXML (`&of=xm`), OAI-PMH | Authoritative per-resolution record: document symbol, date, title, subject headings, and the **vote breakdown field (MARC 967)**. Use to extend Voeten past its lag and to resolve symbols. |
| **UN Documentation Research Guides** (`research.un.org`) | B | HTML | Maps sessions → symbols → meeting records. Needed to join votes to the verbatim record (`A/xx/PV.yy`). |
| **US State Dept, *Voting Practices in the United Nations*** | A | Annual PDF + tables | Publishes "voting coincidence" scores. Useful as an **independently computed baseline** to validate your own agreement math. |

**Key metric caution.** Raw "% of votes identical" is inflated by the ~75–80% of
UNGA resolutions adopted without a vote or by lopsided consensus. Always report
alignment on the **contested subset** (roll-calls where the losing side had ≥10%),
and always report at least one **base-rate comparison dyad** (e.g. Russia–India,
China–India, China–Brazil) so the reader can see whether the number reflects a
Russia–China relationship or just a shared Global South bloc position.

## 2. UN voting — Security Council

| Source | Tier | Access | Notes |
|---|---|---|---|
| **UNDL Security Council voting export** | A | Bulk CSV | 41,349 rows / 2,815 ballots, 1946 to Jan 2026. Held as `data/raw/2026_02_06_sc_voting.csv.gz`. **Adopted resolutions only — see the warning below.** |
| **UNSC veto list** (`main.un.org/securitycouncil/en/content/veto`) + Dag Hammarskjöld Library veto table | A | HTML table, stable | Full historical veto record with symbol, date, subject, and which P5 member(s) vetoed. **This is the only route to vetoes**, because the voting exports exclude them. Small enough to maintain as a CSV. |
| **UNDL, filtered to S/ symbols** | A | MARCXML | Per-draft vote breakdown including abstentions — abstention patterns are more informative than vetoes because they are more frequent. |
| **Security Council Report** `securitycouncilreport.org` | B/C | Monthly Forecast, "In Hindsight" | Best open source on *penholdership*, negotiation history, and who blocked what in closed consultations — i.e. the coordination that never reaches a vote. |
| **UN Meetings Coverage** `press.un.org` | B | Press releases per meeting | Contains explanations-of-vote. This is where you get the **stated justification**, which is the raw material for language-alignment analysis (§5). |

## 3. Joint statements and joint documents

| Source | Tier | Access | Notes |
|---|---|---|---|
| **UN joint letters (China + Russia to the SG / SC President)** | A | UNDL records | *The single most underused coordination artifact.* When Moscow and Beijing want a bilateral text to enter the UN record, they transmit it as a joint letter with a document symbol. Each one is dated, co-signed by both Permanent Representatives, and permanently addressable. Examples in `data/seed/joint_documents.csv`. |
| **Kremlin** `en.kremlin.ru` / `kremlin.ru` | B | HTML + RSS, stable numeric URLs | Full Russian-language and English texts of joint statements, plus the President's daily schedule (the basis for visit counting). |
| **PRC MFA** `fmprc.gov.cn` (EN + ZH) | B | HTML, dated URL slugs | Chinese-language text of the same documents. |
| **Russian MFA** `mid.ru` (RU + EN) | B | HTML + RSS | Readouts of FM-level and consultation-level contacts that never get a leader-level release. |
| **TASS / Xinhua** | B | HTML, wire | Timestamps and sequencing. |

**Technique — trilingual diff.** Every major joint statement exists in Russian,
Chinese, and English. The three versions are *not* translations of each other in
the strict sense; they are negotiated separately. Systematically diffing them
surfaces where the two sides declined to commit to the same thing. Typical
findings: hedging particles in the Chinese text on clauses about Ukraine;
stronger anti-US phrasing in the Russian; formulations present in one language
edition and absent in another. This is a high-yield, low-cost method and it is
almost entirely absent from mainstream commentary.

## 4. Diplomatic contact / visit frequency

| Source | Tier | Access | Notes |
|---|---|---|---|
| **GDELT 2.0 Events** | A | BigQuery (`gdelt-bq.gdeltv2.events`) or CSV/API | CAMEO-coded, 15-minute updates, global. For this dyad: `Actor1CountryCode='RUS' AND Actor2CountryCode='CHN'`, CAMEO root codes `03` (intent to cooperate), `04` (consult), `05` (diplomatic cooperation). Gives you a **time series of contact intensity** rather than a hand-count. Noisy — deduplicate by `GLOBALEVENTID` + day + actor pair, and expect media-volume bias. |
| **ICEWS** (Harvard Dataverse) | A | Bulk TSV, quarterly | Cleaner coding and better actor resolution than GDELT, but lags. Best for validating GDELT trends. |
| **Cline Center POLECAT** | A | Bulk | Successor to Phoenix; PLOVER-coded. |
| **Correlates of War — Diplomatic Exchange (DIPCON)** | A | Bulk CSV, 5-year intervals | Embassy/representation level. Too coarse for events, right for structural baseline. |
| **Pardee Center Diplometrics / FBIC index** | A | Bulk | Bilateral influence capacity scores; good for "is this dyad unusual?" comparisons. |
| **Kremlin schedule + PRC MFA activities pages** | B | HTML | Ground truth for hand-coding leader-level meetings. Cheap because the universe is small (~5–8 leader meetings/year). |
| **ADS-B Exchange / flight tracking** | B | API | Advanced: tracking the Rossiya Special Flight Detachment and PLAAF VIP aircraft can establish visits before or without announcement. Use carefully; high false-positive rate. |

**Structure the output as an event table, not a narrative.** Schema in
`data/schema/event.schema.json`: one row per contact, with `date`, `level`
(leader / head-of-government / FM / deputy-FM / security-council / defence /
party), `venue`, `multilateral_host` (was it a bilateral trip or a pull-aside at
a summit?), `initiator`, `documents_signed`, and `source_url`. The
bilateral-vs-pull-aside distinction matters a lot and is lost in press coverage:
a dedicated state visit and a 40-minute meeting on the margins of an SCO summit
are not the same signal.

## 5. Language and position alignment

| Source | Tier | Access | Notes |
|---|---|---|---|
| **UN verbatim records** (`A/../PV..`, `S/PV..`) via UNDL | A | PDF/text | Full text of every national statement. The corpus for measuring whether the two delegations use the *same formulations* — a much better coordination signal than voting. |
| **UN General Debate Corpus** (Harvard Dataverse, Baturo et al.) | A | Bulk text, 1970–present | Pre-cleaned annual general-debate speeches. Ideal for tracking phrase diffusion. |
| **SCO / BRICS / CSTO summit declarations** | B | HTML | Where bilateral formulations go to become multilateral. Tracking a phrase from a bilateral joint statement → SCO declaration → UNGA resolution language is direct evidence of coordinated norm entrepreneurship. |

**Marker phrases worth tracking as a fixed dictionary:** "indivisible security",
"hegemonism", "Cold War mentality", "bloc confrontation", "colour revolutions",
"legitimate security concerns", "root causes", "unilateral coercive measures",
"double standards", "genuine multilateralism", "sovereign equality",
"external interference", "one-China principle", "indivisibility of security in Europe".
Counting these per-speaker per-year turns rhetoric into a series.

## 6. Corroborating material flows

| Source | Tier | Access |
|---|---|---|
| **UN Comtrade** (`comtradeapi.un.org`) | A | REST + API key |
| **China Customs (GACC)** monthly | A | HTML/XLS |
| **OpenSanctions** | A | Bulk JSON/FtM |
| **Equasis / vessel AIS** for shadow-fleet and Northern Sea Route transits | B | Mixed |


---

## Traps in the official UN voting exports

Found by profiling the committed datasets; each one silently produces a wrong
answer rather than an error. All are encoded in `src/rcwatch/unsc.py` and
`src/rcwatch/ga.py` and covered by tests.

1. **Both exports contain adopted resolutions only.** Failed and vetoed drafts
   are absent — verified by probing for the Sept 2022 Ukraine, March 2024 Gaza
   and Oct 2011 Syria double vetoes, none of which appear. Anyone who reaches for
   a file called `sc_voting.csv` to count vetoes will get zero and may not notice.
   The GA codebook states this; the SC export does not.

2. **GA `session` is not an integer.** `4sp` is the 4th special session and
   `11emsp` the 11th emergency special session (74 of 5,694 resolutions). This is
   undocumented in the codebook, which describes the field only as "session
   number". It matters disproportionately: **ES-11 is the Ukraine session and
   ES-10 is the Palestine session** — the most politically informative votes in
   the file. `int(session)` raises; filtering to `.isdigit()` drops them silently.

3. **`ms_code='CHN'` changes occupant on 25 October 1971**, from the Republic of
   China to the PRC. A continuous 1946–2026 "China" series compares Moscow
   against Taipei for its first 25 years.

4. **`SUN` (USSR) and `RUS` are distinct codes** with no overlapping ballots.
   Splicing them is defensible but must be a stated choice, not an accident.

5. **`permanent_member` is wrong in the SC export** — Somalia is flagged `True`
   on five 2025 ballots. Use a hard-coded P5 list.

6. **`modality='Without Vote'`** rows record no positions and must be excluded
   from any agreement denominator (76 ballots in the SC export).

7. **`ms_name` is the state's name at the time of the vote** and changes across
   the series. Join on `ms_code`.

---

## Ranking: what actually evidences *coordination* vs. mere *alignment*

This is the core analytical problem, and the sources are not equally good at it.
Ordered from strongest to weakest evidence that the two states are **coordinating**
rather than independently arriving at similar positions:

1. **Co-signed documents with a UN symbol** (joint letters, joint statements
   transmitted to the SG). Unambiguous: both governments cleared identical text.
2. **Co-penholding / co-sponsorship of draft resolutions.** Requires prior
   drafting contact. Sponsorship lists are in the UNDL record.
3. **Joint military activity** (announced joint patrols, exercises under an
   annual cooperation plan). Requires months of staff work.
4. **Formulation adoption with a lead-lag** — one side introduces a phrase, the
   other adopts it within weeks. Measurable from the verbatim-record corpus.
5. **Sequenced vetoes and explanations-of-vote** that reference each other.
6. **Simple vote agreement.** Weakest. Cheap, bloc-driven, and inflated by consensus items.

A defensible report should say which tier its claims sit at. Most public
commentary on this dyad is built on tier 6 and presented as if it were tier 1.

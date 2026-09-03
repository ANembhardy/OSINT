"""Dyadic voting-agreement metrics (measures M1-M3 in docs/01-methodology.md).

Pure stdlib so it runs anywhere. Input is a long-format vote table:

    rcid,session,country,vote

using the Voeten/UNGA vote coding:

    1 = yes, 2 = abstain, 3 = no, 8 = absent, 9 = not a member

The important part of this module is not the arithmetic, which is trivial. It is
that every result carries the divergence typology and is expected to be reported
against baseline dyads -- see `compare_baselines`.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Iterable, Mapping, Sequence

YES, ABSTAIN, NO, ABSENT, NOT_MEMBER = 1, 2, 3, 8, 9
PRESENT = (YES, ABSTAIN, NO)

VOTE_NAMES = {YES: "yes", ABSTAIN: "abstain", NO: "no", ABSENT: "absent", NOT_MEMBER: "not_member"}


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def load_votes(path: str) -> dict[str, dict[str, int]]:
    """Read a long-format vote table into {rcid: {country: vote}}."""
    table: dict[str, dict[str, int]] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["rcid"]][row["country"].upper()] = int(row["vote"])
    return dict(table)


def load_sessions(path: str) -> dict[str, str]:
    """Read {rcid: session} so results can be broken out by year/session."""
    with open(path, newline="", encoding="utf-8") as fh:
        return {row["rcid"]: row.get("session", "") for row in csv.DictReader(fh)}


# --------------------------------------------------------------------------- #
# subsetting
# --------------------------------------------------------------------------- #

def is_contested(ballot: Mapping[str, int], threshold: float = 0.10) -> bool:
    """True when the losing side held at least `threshold` of votes cast.

    Consensus and near-consensus resolutions dominate the UNGA record and inflate
    every pairwise agreement score. Excluding them is the single most important
    correction when reporting alignment.
    """
    cast = [v for v in ballot.values() if v in PRESENT]
    if not cast:
        return False
    counts = [sum(1 for v in cast if v == opt) for opt in PRESENT]
    return (len(cast) - max(counts)) / len(cast) >= threshold


def contested(table: Mapping[str, Mapping[str, int]], threshold: float = 0.10) -> dict[str, Mapping[str, int]]:
    return {rcid: b for rcid, b in table.items() if is_contested(b, threshold)}


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #

@dataclass
class Divergence:
    """One non-identical vote, classified per measure M3."""

    rcid: str
    kind: str          # identical | partial_split | opposed | absence
    a_vote: str
    b_vote: str


@dataclass
class AgreementResult:
    a: str
    b: str
    comparable: int = 0            # ballots where both were present
    identical: int = 0
    partial_split: int = 0         # one yes/no, the other abstain
    opposed: int = 0               # one yes, the other no
    absence: int = 0               # one present, the other absent (excluded from `comparable`)
    divergences: list[Divergence] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        """Exact-match rate. Treats a partial split as total disagreement."""
        return self.identical / self.comparable if self.comparable else float("nan")

    @property
    def s_score(self) -> float:
        """Lijphart agreement index: identical 1.0, partial split 0.5, opposed 0.0.

        **Prefer this to `agreement` for anything substantive.** An abstention
        opposite a yes or a no is *partial alignment*, not disagreement: the
        abstaining state is declining to endorse the text while also declining to
        oppose it. In the Security Council the asymmetry is sharper still --
        where one permanent member vetoes and the other abstains, the abstainer
        withholds the second veto but also withholds support, which is
        cover rather than defection.

        The two measures can differ enormously. On the nine Ukraine emergency
        special session texts, Russia-China exact agreement is 22.2% and the
        S-score is 61.1%, because seven of the nine divergences are China
        abstaining while Russia votes no.
        """
        if not self.comparable:
            return float("nan")
        return (self.identical + 0.5 * self.partial_split) / self.comparable

    @property
    def opposed_rate(self) -> float:
        return self.opposed / self.comparable if self.comparable else float("nan")

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("divergences")
        d["agreement"] = round(self.agreement, 4) if self.comparable else None
        d["s_score"] = round(self.s_score, 4) if self.comparable else None
        d["opposed_rate"] = round(self.opposed_rate, 4) if self.comparable else None
        return d


def score(
    table: Mapping[str, Mapping[str, int]],
    a: str,
    b: str,
    keep_divergences: bool = True,
) -> AgreementResult:
    """Compute M1 agreement plus the M3 divergence typology for one dyad."""
    a, b = a.upper(), b.upper()
    res = AgreementResult(a=a, b=b)

    for rcid, ballot in table.items():
        va, vb = ballot.get(a), ballot.get(b)
        if va is None or vb is None or NOT_MEMBER in (va, vb):
            continue
        if va == ABSENT or vb == ABSENT:
            if va != vb:                    # one showed up, the other did not
                res.absence += 1
                if keep_divergences:
                    res.divergences.append(
                        Divergence(rcid, "absence", VOTE_NAMES[va], VOTE_NAMES[vb])
                    )
            continue

        res.comparable += 1
        if va == vb:
            res.identical += 1
            continue

        kind = "opposed" if {va, vb} == {YES, NO} else "partial_split"
        setattr(res, kind, getattr(res, kind) + 1)
        if keep_divergences:
            res.divergences.append(Divergence(rcid, kind, VOTE_NAMES[va], VOTE_NAMES[vb]))

    return res


def by_session(
    table: Mapping[str, Mapping[str, int]],
    sessions: Mapping[str, str],
    a: str,
    b: str,
) -> dict[str, AgreementResult]:
    """Agreement broken out per session, for trend lines."""
    buckets: dict[str, dict[str, Mapping[str, int]]] = defaultdict(dict)
    for rcid, ballot in table.items():
        buckets[sessions.get(rcid, "unknown")][rcid] = ballot
    return {s: score(sub, a, b, keep_divergences=False) for s, sub in sorted(buckets.items())}


DEFAULT_BASELINES: tuple[tuple[str, str], ...] = (
    ("RUS", "IND"),
    ("CHN", "IND"),
    ("CHN", "BRA"),
    ("RUS", "IRN"),
    ("CHN", "PAK"),
    ("USA", "GBR"),   # a genuinely aligned dyad, for scale
)


def compare_baselines(
    table: Mapping[str, Mapping[str, int]],
    focus: tuple[str, str] = ("RUS", "CHN"),
    baselines: Sequence[tuple[str, str]] = DEFAULT_BASELINES,
) -> list[dict]:
    """Measure M2. Never report the focus dyad without this."""
    rows = [score(table, *focus, keep_divergences=False).summary() | {"role": "focus"}]
    for pair in baselines:
        rows.append(score(table, *pair, keep_divergences=False).summary() | {"role": "baseline"})
    return rows


def mean_pairwise(
    table: Mapping[str, Mapping[str, int]],
    countries: Iterable[str],
    *,
    measure: str = "agreement",
) -> float:
    """Mean pairwise score across a caucus -- the bloc-effect control.

    `measure` must be "agreement" (exact match) or "s_score" (graded). Compare
    like with like: an S-score for the focus dyad against an exact-match baseline
    would flatter the dyad by roughly 15 points.
    """
    if measure not in ("agreement", "s_score"):
        raise ValueError(f"unknown measure {measure!r}")
    cs = sorted({c.upper() for c in countries})
    vals = [
        getattr(score(table, x, y, keep_divergences=False), measure)
        for i, x in enumerate(cs)
        for y in cs[i + 1:]
    ]
    vals = [v for v in vals if v == v]     # drop NaN
    return sum(vals) / len(vals) if vals else float("nan")


def withheld_from_majority(
    table: Mapping[str, Mapping[str, int]], country: str
) -> dict:
    """How often a state declines to join the winning side.

    Exact-match scores miss the thing that matters on lopsided votes: a state
    that abstains against a 141-vote majority has taken a position, and it is not
    a neutral one. This counts, over ballots the state was present for, how often
    it voted with the majority position versus withholding (abstaining) or
    opposing it.
    """
    country = country.upper()
    with_maj = withheld = against = 0
    for ballot in table.values():
        v = ballot.get(country)
        if v is None or v in (ABSENT, NOT_MEMBER):
            continue
        cast = [x for x in ballot.values() if x in PRESENT]
        if not cast:
            continue
        majority = max(PRESENT, key=lambda opt: sum(1 for x in cast if x == opt))
        if v == majority:
            with_maj += 1
        elif v == ABSTAIN:
            withheld += 1
        else:
            against += 1
    total = with_maj + withheld + against
    return {
        "country": country,
        "ballots": total,
        "with_majority": with_maj,
        "withheld": withheld,
        "against": against,
        "withheld_or_against_rate": round((withheld + against) / total, 4) if total else None,
    }

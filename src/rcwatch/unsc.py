"""Loader for the UN Digital Library Security Council voting export.

The export is one row per member state per ballot, with columns:

    undl_id, ms_code, ms_name, permanent_member, ms_vote, date, resolution,
    draft, meeting, description, agenda, subjects, vote_note, total_yes,
    total_no, total_abstentions, total_non_voting, total_ms, modality, undl_link

Four traps are encoded here because each one silently produces a wrong answer:

1. **ADOPTED RESOLUTIONS ONLY.** Every ballot in the export carries an `S/RES/`
   symbol, which a draft only receives once it passes. Vetoed drafts fail and are
   absent -- verified against the September 2022 Ukraine, March 2024 Gaza and
   October 2011 Syria double vetoes, none of which appear. **This file cannot be
   used to study vetoes**, and any veto count derived from it will be ~zero. Use
   it for abstention behaviour on adopted texts, which is the more frequent and
   arguably more informative signal anyway.

2. **`ms_code='CHN'` changes occupant on 25 October 1971**, from the Republic of
   China (Taipei) to the People's Republic. Treating the series as continuous
   compares Moscow against Taipei for the first 25 years. `CHINA_SEAT_CHANGE`
   below; `load()` tags every row with `china_seat`.

3. **`SUN` (USSR) and `RUS` are separate codes** with no overlapping ballots
   (USSR to 1991, Russia from 1992). Decide explicitly whether you want the
   post-Soviet series or a spliced one; `russia_actor=` makes that choice visible.

4. **`permanent_member` is unreliable.** Somalia is flagged `True` on five 2025
   ballots. Trust `PERMANENT_MEMBERS` below, not the column.

Also note `modality='Without Vote'` rows: adopted by consensus with no recorded
ballot. They must be excluded from any agreement denominator.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .agreement import YES, ABSTAIN, NO, ABSENT

#: UNDL vote letters -> the Voeten coding used by rcwatch.agreement
VOTE_MAP = {"Y": YES, "A": ABSTAIN, "N": NO, "X": ABSENT}

#: The date the China seat passed from Taipei to Beijing (UNGA res. 2758).
CHINA_SEAT_CHANGE = "1971-10-25"

#: The last USSR ballot precedes the first Russian Federation ballot; no overlap.
USSR_SUCCESSION = "1992-01-01"

PERMANENT_MEMBERS = frozenset({"CHN", "FRA", "GBR", "RUS", "SUN", "USA"})


def _open(path: str):
    """Open a UNDL export, transparently handling gzip."""
    if str(path).endswith(".gz"):
        import gzip

        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return open(path, newline="", encoding="utf-8-sig")


@dataclass
class Ballot:
    undl_id: str
    date: str
    resolution: str
    draft: str
    meeting: str
    description: str
    modality: str
    votes: dict[str, int] = field(default_factory=dict)

    @property
    def year(self) -> int:
        return int(self.date[:4])

    @property
    def china_seat(self) -> str:
        return "PRC" if self.date >= CHINA_SEAT_CHANGE else "ROC"

    @property
    def unanimous(self) -> bool:
        cast = [v for v in self.votes.values() if v != ABSENT]
        return all(v == YES for v in cast)

    @property
    def url(self) -> str:
        return f"https://digitallibrary.un.org/record/{self.undl_id}"


def load(path: str, *, votes_only: bool = True) -> list[Ballot]:
    """Read the export into ballots.

    `votes_only` drops `modality='Without Vote'` ballots, which have no recorded
    positions and would otherwise inflate every agreement denominator.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            grouped[row["undl_id"]].append(row)

    ballots = []
    for undl_id, rows in grouped.items():
        h = rows[0]
        if votes_only and h["modality"] != "Vote":
            continue
        ballots.append(
            Ballot(
                undl_id=undl_id,
                date=h["date"],
                resolution=h["resolution"],
                draft=h["draft"],
                meeting=h["meeting"],
                description=h["description"],
                modality=h["modality"],
                votes={r["ms_code"]: VOTE_MAP.get(r["ms_vote"], ABSENT) for r in rows},
            )
        )
    return sorted(ballots, key=lambda b: (b.date, b.undl_id))


def russia_code(ballot: Ballot) -> str:
    """Which code carries the Russian seat on this ballot."""
    return "RUS" if ballot.date >= USSR_SUCCESSION else "SUN"


def to_vote_table(
    ballots: list[Ballot],
    *,
    russia_actor: str = "RUS",
    china_seat: str | None = "PRC",
) -> dict[str, dict[str, int]]:
    """Build a table for `rcwatch.agreement`, normalising the Russian seat.

    russia_actor:
        "RUS"     post-Soviet Russia only (default; the honest modern series)
        "SUN"     USSR only
        "spliced" USSR and Russia as one continuous actor, emitted as "RUS"
    china_seat:
        "PRC"     ballots from 25 Oct 1971 only (default)
        "ROC"     pre-1971 ballots only
        None      no filter -- only sensible if China is not part of the analysis
    """
    if russia_actor not in ("RUS", "SUN", "spliced"):
        raise ValueError(f"unknown russia_actor {russia_actor!r}")

    table: dict[str, dict[str, int]] = {}
    for b in ballots:
        if china_seat and b.china_seat != china_seat:
            continue

        votes = dict(b.votes)
        if russia_actor == "spliced":
            code = russia_code(b)
            if code == "SUN" and "SUN" in votes:
                votes["RUS"] = votes.pop("SUN")
        elif russia_actor not in votes:
            continue

        table[b.undl_id] = votes
    return table


def contested(ballots: list[Ballot]) -> list[Ballot]:
    """Non-unanimous ballots.

    The Council adopts most resolutions unanimously, so the ~10% minority rule
    used for the General Assembly is the wrong instrument here: on a 15-member
    body a single abstention is 6.7% and would be discarded. Any recorded
    dissent counts.
    """
    return [b for b in ballots if not b.unanimous]


def audit(path: str) -> dict:
    """Data-quality report for a fresh export."""
    with _open(path) as fh:
        rows = list(csv.DictReader(fh))

    ballots = {r["undl_id"] for r in rows}
    adopted = {r["undl_id"] for r in rows if r["resolution"].startswith("S/RES")}
    bad_perm = sorted(
        {r["ms_code"] for r in rows
         if r["permanent_member"] == "True" and r["ms_code"] not in PERMANENT_MEMBERS}
    )
    return {
        "rows": len(rows),
        "ballots": len(ballots),
        "date_range": [min(r["date"] for r in rows), max(r["date"] for r in rows)],
        "adopted_resolutions": len(adopted),
        "failed_or_vetoed_drafts": len(ballots) - len(adopted),
        "scope_warning": (
            "Export contains adopted resolutions only; vetoed drafts are absent. "
            "Veto analysis is impossible from this file."
        ) if len(adopted) == len(ballots) else "",
        "vote_codes": dict(Counter(r["ms_vote"] for r in rows)),
        "modalities": dict(Counter(r["modality"] for r in rows)),
        "permanent_member_column_errors": bad_perm,
    }

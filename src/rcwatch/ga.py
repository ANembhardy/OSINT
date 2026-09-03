"""Loader for the Dag Hammarskjold Library General Assembly voting dataset.

Source: UN Digital Library record 4060887, "General Assembly Voting Data",
version 5 (February 2026), covering resolution 1 (11 Dec 1946) to 80/246
(30 Dec 2025); 947,434 rows, one per member state per resolution.
Codebook mirrored at docs/reference/ga_voting_codebook_v5.md.
Copyright United Nations; non-commercial use with attribution.

**Scope, stated in the publisher's own summary and load-bearing for every number
derived from it:**

* only resolutions *adopted* through a **recorded vote** are present;
* drafts that **failed to be adopted are excluded** -- so, exactly as with the
  Security Council export, this file cannot speak to blocked or defeated texts;
* votes on **individual paragraphs** are excluded, which removes a real venue for
  coordinated behaviour (paragraph-level splits are where delegations often
  register disagreement without opposing a whole text);
* resolutions adopted **without a vote** never appear at all.

That last point cuts the other way from the Security Council file: the ~75-80%
of Assembly business done by consensus is already absent, so the denominator here
is closer to the contested universe than a naive reading of the General Assembly
record would suggest. Applying a further contested filter (`agreement.contested`)
still helps, because many recorded votes are near-unanimous.

`ms_name` is the state's official name *at the time of the vote*, so it changes
across the series; join on `ms_code`. Note the same successor-state and seat
questions as the Council data: USSR/Russia, and the 1971 China seat change.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .unsc import CHINA_SEAT_CHANGE, USSR_SUCCESSION, VOTE_MAP, _open

#: Canonical citation, per the publisher's terms of use.
CITATION = (
    "United Nations Dag Hammarskjold Library, General Assembly Voting Data, "
    "United Nations, version 5 (February 2026), 2026, downloaded from "
    "https://digitallibrary.un.org/record/4060887"
)

#: Session codes are NOT plain integers, and the codebook does not say so.
#: A regular session is "79"; a special session is "4sp"; an emergency special
#: session is "11emsp". 74 of 5,694 resolutions carry a suffixed code. This
#: matters more than the count suggests: emergency special sessions are where
#: the most politically charged votes live -- ES-10 (occupied Palestinian
#: territory) and ES-11 (Ukraine) among them. Code that coerces `session` with
#: int() crashes on these, and code that filters to digits silently drops them.
SESSION_RE = re.compile(r"^(?P<number>\d+)(?P<kind>emsp|sp)?$")

SESSION_KINDS = {None: "regular", "sp": "special", "emsp": "emergency_special"}

#: Columns the loader relies on; the export carries more.
REQUIRED_COLUMNS = ("undl_id", "ms_code", "ms_vote", "date", "session", "resolution")


@dataclass
class Resolution:
    undl_id: str
    date: str
    session: str
    resolution: str
    title: str
    votes: dict[str, int] = field(default_factory=dict)

    @property
    def year(self) -> int:
        return int(self.date[:4])

    @property
    def china_seat(self) -> str:
        return "PRC" if self.date >= CHINA_SEAT_CHANGE else "ROC"

    @property
    def session_kind(self) -> str:
        """regular | special | emergency_special | unknown"""
        m = SESSION_RE.match(self.session or "")
        return SESSION_KINDS[m.group("kind")] if m else "unknown"

    @property
    def session_number(self) -> int | None:
        m = SESSION_RE.match(self.session or "")
        return int(m.group("number")) if m else None

    @property
    def url(self) -> str:
        return f"https://digitallibrary.un.org/record/{self.undl_id}"


def load(path: str, *, keep_title: bool = False) -> list[Resolution]:
    """Read the GA export.

    Streams row by row and materialises one `Resolution` per `undl_id` on first
    sight, keeping only the vote map rather than the source rows -- the version 5
    export is ~947k rows / 364 MB, and buffering it whole does not fit in memory.
    `keep_title=False` drops the repeated title text for the same reason.
    """
    out: dict[str, Resolution] = {}
    with _open(path) as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{path} is missing required columns {missing}. "
                "Expected the Dag Hammarskjold Library GA voting export "
                "(https://digitallibrary.un.org/record/4060887), not its codebook."
            )
        for row in reader:
            res = out.get(row["undl_id"])
            if res is None:
                res = out[row["undl_id"]] = Resolution(
                    undl_id=row["undl_id"],
                    date=row["date"],
                    session=row.get("session", ""),
                    resolution=row["resolution"],
                    title=row.get("title", "") if keep_title else "",
                )
            res.votes[row["ms_code"]] = VOTE_MAP.get(row["ms_vote"], 8)

    return sorted(out.values(), key=lambda r: (r.date, r.undl_id))


def to_vote_table(
    resolutions: list[Resolution],
    *,
    russia_actor: str = "RUS",
    china_seat: str | None = "PRC",
) -> dict[str, dict[str, int]]:
    """Build a table for `rcwatch.agreement`. Semantics match `unsc.to_vote_table`."""
    table: dict[str, dict[str, int]] = {}
    for r in resolutions:
        if china_seat and r.china_seat != china_seat:
            continue
        votes = dict(r.votes)
        if russia_actor == "spliced":
            if r.date < USSR_SUCCESSION and "SUN" in votes:
                votes["RUS"] = votes.pop("SUN")
        elif russia_actor not in votes:
            continue
        table[r.undl_id] = votes
    return table


def sessions(resolutions: list[Resolution]) -> dict[str, str]:
    """{undl_id: session} for `agreement.by_session`, codes kept verbatim."""
    return {r.undl_id: r.session for r in resolutions}


def regular_sessions(resolutions: list[Resolution]) -> list[Resolution]:
    """Regular sessions only -- the comparable annual series.

    Special and emergency special sessions are convened for single crises and
    have a quite different vote mix, so mixing them into a per-session trend line
    creates spurious jumps.
    """
    return [r for r in resolutions if r.session_kind == "regular"]


def session_sort_key(code: str) -> tuple[int, int]:
    """Sort session codes so regular sessions order numerically and
    special/emergency sessions sort after the regular series rather than
    crashing an int() call."""
    m = SESSION_RE.match(code or "")
    if not m:
        return (3, 0)
    rank = {None: 0, "sp": 1, "emsp": 2}[m.group("kind")]
    return (rank, int(m.group("number")))

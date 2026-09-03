"""UN Digital Library client.

UNDL is an Invenio instance: its search endpoint speaks MARCXML when given
`of=xm`, which makes it the only fully machine-readable route to per-resolution
UN voting records that stays current (unlike the Voeten dataset, which lags a
year).

Fields that matter here:

    245  title
    269 / 260  date
    791  document symbol
    967  vote line, one subfield per member state:  "Y RUSSIAN FEDERATION"

Voting-record collection id is 'Voting Data' (`fct__2` facet); resolutions carry
symbols beginning `A/RES/` (Assembly) or `S/RES/` (Council).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .http import get

BASE = "https://digitallibrary.un.org/search"
MARC_NS = {"m": "http://www.loc.gov/MARC21/slim"}

VOTE_PREFIX = {"Y": 1, "A": 2, "N": 3}      # yes / abstain / no -> Voeten coding


@dataclass
class VotingRecord:
    record_id: str
    symbol: str = ""
    title: str = ""
    date: str = ""
    votes: dict[str, int] = field(default_factory=dict)   # country name -> code

    @property
    def url(self) -> str:
        return f"https://digitallibrary.un.org/record/{self.record_id}"


def _subfield(datafield: ET.Element, code: str) -> str:
    el = datafield.find(f"m:subfield[@code='{code}']", MARC_NS)
    return (el.text or "").strip() if el is not None else ""


def parse_marcxml(xml_text: str) -> list[VotingRecord]:
    """Parse a MARCXML collection into VotingRecord objects."""
    root = ET.fromstring(xml_text)
    out: list[VotingRecord] = []

    for rec in root.iter("{http://www.loc.gov/MARC21/slim}record"):
        cf = rec.find("m:controlfield[@tag='001']", MARC_NS)
        vr = VotingRecord(record_id=(cf.text or "").strip() if cf is not None else "")

        for df in rec.findall("m:datafield", MARC_NS):
            tag = df.get("tag")
            if tag == "245":
                vr.title = _subfield(df, "a")
            elif tag in ("269", "260"):
                vr.date = vr.date or _subfield(df, "a") or _subfield(df, "c")
            elif tag == "791":
                vr.symbol = vr.symbol or _subfield(df, "a")
            elif tag == "967":
                raw = _subfield(df, "e") or _subfield(df, "d") or _subfield(df, "a")
                m = re.match(r"^\s*([YNA])\s+(.+?)\s*$", raw)
                if m:
                    vr.votes[m.group(2).upper()] = VOTE_PREFIX[m.group(1)]
                elif raw:                       # no prefix = non-voting / absent
                    vr.votes[raw.upper()] = 8
        out.append(vr)

    return out


def search(query: str, *, collection: str = "Voting Data", limit: int = 50, offset: int = 0) -> list[VotingRecord]:
    """Search UNDL and return parsed voting records.

    Example:
        search('191 "Ukraine"', limit=25)
    """
    xml_text = get(
        BASE,
        params={"p": query, "fct__2": collection, "rg": limit, "jrec": offset + 1, "of": "xm"},
    )
    return parse_marcxml(xml_text)


def to_long_rows(records: list[VotingRecord]) -> list[dict]:
    """Flatten to the long format consumed by rcwatch.agreement."""
    return [
        {"rcid": r.record_id, "session": r.date[:4], "country": country, "vote": code}
        for r in records
        for country, code in r.votes.items()
    ]

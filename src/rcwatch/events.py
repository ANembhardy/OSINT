"""Diplomatic-contact table: loading, validation and measure-M5 indicators."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass

LEVELS = (
    "leader",
    "head_of_government",
    "deputy_head_of_government",
    "foreign_minister",
    "deputy_foreign_minister",
    "security_council",
    "defence",
    "party",
)

VENUE_TYPES = ("state_visit", "bilateral_visit", "summit_pullaside", "commemorative", "virtual")


@dataclass
class Contact:
    date: str
    level: str
    host_country: str
    city: str
    venue_type: str
    participants: str
    multilateral_host: str
    documents_signed: int
    summary: str
    source_url: str
    verification: str

    @property
    def year(self) -> int:
        return int(self.date[:4])

    @property
    def is_dedicated(self) -> bool:
        """A trip made for its own sake, as opposed to a meeting on summit margins."""
        return self.venue_type in ("state_visit", "bilateral_visit")


def load(path: str) -> list[Contact]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append(
            Contact(
                date=r["date"],
                level=r["level"],
                host_country=r["host_country"],
                city=r["city"],
                venue_type=r["venue_type"],
                participants=r["participants"],
                multilateral_host=r.get("multilateral_host", ""),
                documents_signed=int(r.get("documents_signed") or 0),
                summary=r.get("summary", ""),
                source_url=r.get("source_url", ""),
                verification=r.get("verification", ""),
            )
        )
    return out


def validate(contacts: list[Contact]) -> list[str]:
    """Return a list of data-quality problems. Empty list means the table is clean."""
    problems = []
    for c in contacts:
        if c.level not in LEVELS:
            problems.append(f"{c.date}: unknown level {c.level!r}")
        if c.venue_type not in VENUE_TYPES:
            problems.append(f"{c.date}: unknown venue_type {c.venue_type!r}")
        if c.venue_type == "summit_pullaside" and not c.multilateral_host:
            problems.append(f"{c.date}: pull-aside with no multilateral_host recorded")
        if c.verification == "verified" and not c.source_url:
            problems.append(f"{c.date}: marked verified but carries no source_url")
    return problems


def indicators(contacts: list[Contact], level: str = "leader") -> dict:
    """Measure M5: tempo, reciprocity, venue mix and document yield."""
    sel = [c for c in contacts if c.level == level]
    per_year = Counter(c.year for c in sel)
    hosts = Counter(c.host_country for c in sel)
    venues = Counter(c.venue_type for c in sel)
    docs = sum(c.documents_signed for c in sel)

    dedicated = sum(1 for c in sel if c.is_dedicated)
    return {
        "level": level,
        "contacts": len(sel),
        "per_year": dict(sorted(per_year.items())),
        "host_split": dict(hosts),
        "venue_mix": dict(venues),
        "dedicated_share": round(dedicated / len(sel), 3) if sel else None,
        "documents_signed": docs,
        "documents_per_contact": round(docs / len(sel), 2) if sel else None,
        "reciprocity_ratio": round(hosts.get("RU", 0) / hosts["CN"], 2) if hosts.get("CN") else None,
        "verified_share": round(
            sum(1 for c in sel if c.verification == "verified") / len(sel), 3
        ) if sel else None,
    }


def timeline(contacts: list[Contact]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = defaultdict(list)
    for c in sorted(contacts, key=lambda c: c.date):
        out[c.year].append(f"{c.date} [{c.level}] {c.city or '-'} ({c.venue_type})")
    return dict(out)

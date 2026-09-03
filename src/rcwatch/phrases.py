"""Marker-phrase tracking (measure M6).

Turns shared rhetoric into a countable series. The dictionary below is the
working set from docs/02-source-inventory.md section 5; keep it fixed across
runs, because changing the dictionary changes every historical number.
"""

from __future__ import annotations

import re
from collections import Counter

MARKERS: dict[str, list[str]] = {
    "indivisible_security": ["indivisible security", "indivisibility of security"],
    "hegemonism": ["hegemonism", "hegemonic", "unilateral hegemony"],
    "cold_war_mentality": ["cold war mentality", "cold-war mentality"],
    "bloc_confrontation": ["bloc confrontation", "bloc politics"],
    "colour_revolution": ["colour revolution", "color revolution"],
    "legitimate_security_concerns": ["legitimate security concerns", "legitimate security interests"],
    "root_causes": ["root causes of the crisis", "root causes of the conflict"],
    "unilateral_coercive_measures": ["unilateral coercive measures", "illegal unilateral sanctions"],
    "double_standards": ["double standards"],
    "genuine_multilateralism": ["genuine multilateralism", "true multilateralism"],
    "sovereign_equality": ["sovereign equality"],
    "external_interference": ["external interference", "interference in internal affairs"],
    "one_china": ["one-china principle", "one china principle"],
    "multipolar": ["multipolar world", "multipolarity"],
    "un_central_role": ["central role of the united nations", "un-centred", "un-centered"],
}


def count(text: str, markers: dict[str, list[str]] | None = None) -> Counter:
    """Count marker hits in a document. Case-insensitive, whitespace-tolerant."""
    markers = markers or MARKERS
    norm = re.sub(r"\s+", " ", text.lower())
    hits = Counter()
    for label, variants in markers.items():
        for v in variants:
            hits[label] += len(re.findall(re.escape(v.lower()), norm))
    return +hits          # unary plus drops zero counts


def lead_lag(series_a: dict[str, str], series_b: dict[str, str], marker: str) -> dict:
    """First appearance of a marker in each side's corpus.

    `series_*` maps an ISO date to document text. A consistently negative lag
    across many markers is evidence about who sets the vocabulary of the
    partnership -- a question vote counting cannot reach.
    """
    def first(series):
        dates = [d for d, txt in sorted(series.items()) if count(txt).get(marker)]
        return dates[0] if dates else None

    fa, fb = first(series_a), first(series_b)
    return {"marker": marker, "first_a": fa, "first_b": fb, "leader": (
        None if not (fa and fb) else "a" if fa < fb else "b" if fb < fa else "tie"
    )}

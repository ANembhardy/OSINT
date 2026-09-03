import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rcwatch import events

SEED = str(ROOT / "data" / "seed" / "meetings.csv")


def test_seed_table_is_clean():
    assert events.validate(events.load(SEED)) == []


def test_verified_rows_carry_a_source():
    for c in events.load(SEED):
        if c.verification == "verified":
            assert c.source_url, f"{c.date} verified without a source"


def test_pullaside_vs_dedicated_distinction():
    contacts = events.load(SEED)
    ind = events.indicators(contacts, "leader")
    assert 0.0 <= ind["dedicated_share"] <= 1.0
    assert ind["contacts"] == sum(ind["per_year"].values())
    assert sum(ind["venue_mix"].values()) == ind["contacts"]


def test_indicators_handle_empty_level():
    ind = events.indicators([], "leader")
    assert ind["contacts"] == 0 and ind["dedicated_share"] is None

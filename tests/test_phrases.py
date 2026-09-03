import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rcwatch import phrases


def test_counts_are_case_and_space_insensitive():
    hits = phrases.count("Cold  War\nMentality and COLD WAR MENTALITY")
    assert hits["cold_war_mentality"] == 2


def test_zero_counts_are_dropped():
    assert "one_china" not in phrases.count("multipolar world")


def test_lead_lag_identifies_first_user():
    a = {"2021-01-01": "hegemonism", "2022-01-01": "hegemonism"}
    b = {"2023-01-01": "hegemonism"}
    assert phrases.lead_lag(a, b, "hegemonism")["leader"] == "a"


def test_lead_lag_handles_missing():
    assert phrases.lead_lag({"2021-01-01": "nothing"}, {}, "hegemonism")["leader"] is None

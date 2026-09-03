import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rcwatch import agreement as ag

FIX = str(Path(__file__).parent / "fixtures" / "votes.csv")


def table():
    return ag.load_votes(FIX)


def test_loads_long_format():
    t = table()
    assert len(t) == 11                      # 6 consensus + 5 keyed roll-calls
    assert t["k1"]["RUS"] == ag.NO


def test_contested_filter_drops_consensus():
    t = table()
    c = ag.contested(t)
    assert set(c) == {"k1", "k2", "k3", "k4", "k5"}
    assert all(not k.startswith("c") for k in c)


def test_raw_agreement_is_inflated_by_consensus():
    """The headline point of measure M1: the subset choice moves the number a lot."""
    t = table()
    raw = ag.score(t, "RUS", "CHN")
    con = ag.score(ag.contested(t), "RUS", "CHN")

    assert raw.comparable == 10              # k5 excluded: China absent
    assert raw.identical == 8
    assert raw.agreement == 0.8

    assert con.comparable == 4
    assert con.identical == 2
    assert con.agreement == 0.5
    assert raw.agreement > con.agreement


def test_divergence_typology():
    con = ag.score(ag.contested(table()), "RUS", "CHN")
    kinds = {d.rcid: d.kind for d in con.divergences}
    assert kinds["k3"] == "partial_split"
    assert kinds["k4"] == "opposed"
    assert kinds["k5"] == "absence"
    assert con.opposed == 1
    assert con.partial_split == 1
    assert con.absence == 1


def test_absence_excluded_from_denominator():
    con = ag.score(ag.contested(table()), "RUS", "CHN")
    assert con.comparable == con.identical + con.partial_split + con.opposed


def test_by_session_splits_trend():
    t = table()
    per = ag.by_session(t, ag.load_sessions(FIX), "RUS", "CHN")
    assert set(per) == {"78", "79"}
    assert per["78"].agreement == 1.0        # aligned in session 78
    assert per["79"].agreement == 0.0        # both divergences fall in 79


def test_baselines_include_focus_and_controls():
    rows = ag.compare_baselines(table())
    assert rows[0]["role"] == "focus"
    assert rows[0]["a"] == "RUS" and rows[0]["b"] == "CHN"
    assert any(r["role"] == "baseline" for r in rows)
    assert all("agreement" in r for r in rows)


def test_mean_pairwise_bloc_control():
    m = ag.mean_pairwise(table(), ["RUS", "CHN", "IND", "IRN", "PAK"])
    assert 0.0 <= m <= 1.0

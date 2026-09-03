import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest

from rcwatch import agreement as ag
from rcwatch import ga, unsc

DATA = ROOT / "data" / "raw" / "2026_02_06_sc_voting.csv.gz"
pytestmark = pytest.mark.skipif(not DATA.exists(), reason="SC export not present")


@pytest.fixture(scope="module")
def ballots():
    return unsc.load(str(DATA))


def test_export_is_adopted_resolutions_only(ballots):
    """The load-bearing scope constraint: no failed or vetoed drafts."""
    rep = unsc.audit(str(DATA))
    assert rep["failed_or_vetoed_drafts"] == 0
    assert "vetoed drafts are absent" in rep["scope_warning"]
    assert all(b.resolution.startswith("S/RES") for b in ballots)


def test_known_vetoed_drafts_are_absent(ballots):
    """Spot-check three well-documented vetoes; none may appear."""
    dates = {b.date for b in ballots}
    for vetoed in ("2022-09-30", "2024-03-22", "2011-10-04"):
        assert vetoed not in dates


def test_without_vote_ballots_excluded_by_default():
    assert all(b.modality == "Vote" for b in unsc.load(str(DATA)))
    assert len(unsc.load(str(DATA), votes_only=False)) > len(unsc.load(str(DATA)))


def test_china_seat_change_is_tagged(ballots):
    assert {b.china_seat for b in ballots} == {"ROC", "PRC"}
    assert all(b.china_seat == "PRC" for b in ballots if b.date >= unsc.CHINA_SEAT_CHANGE)


def test_ussr_and_russia_never_overlap(ballots):
    assert not any("SUN" in b.votes and "RUS" in b.votes for b in ballots)
    assert all(unsc.russia_code(b) == "RUS" for b in ballots if b.date >= unsc.USSR_SUCCESSION)


def test_permanent_member_column_is_unreliable():
    """Somalia is flagged permanent on 2025 ballots; trust the constant instead."""
    assert unsc.audit(str(DATA))["permanent_member_column_errors"] == ["SOM"]
    assert "SOM" not in unsc.PERMANENT_MEMBERS


def test_default_table_scopes_to_prc_and_post_soviet(ballots):
    tbl = unsc.to_vote_table(ballots)
    assert all("RUS" in v for v in tbl.values())
    assert len(tbl) < len(ballots)


def test_spliced_actor_emits_russia_for_soviet_ballots(ballots):
    soviet = [b for b in ballots if b.date < unsc.USSR_SUCCESSION]
    tbl = unsc.to_vote_table(soviet, russia_actor="spliced", china_seat=None)
    assert tbl and all("RUS" in v and "SUN" not in v for v in tbl.values())


def test_rejects_unknown_actor(ballots):
    with pytest.raises(ValueError):
        unsc.to_vote_table(ballots, russia_actor="USSR")


def test_contested_uses_any_dissent_not_a_ten_percent_rule(ballots):
    """One abstention out of 15 is 6.7% and must still count as contested."""
    con = unsc.contested(ballots)
    assert all(not b.unanimous for b in con)
    assert any(
        sum(1 for v in b.votes.values() if v == ag.ABSTAIN) == 1 for b in con
    )


def test_headline_result_is_reproducible(ballots):
    """Guards the numbers quoted in docs/03-findings-2026-09.md."""
    scoped = [b for b in ballots
              if b.china_seat == "PRC" and b.date >= unsc.USSR_SUCCESSION]
    con = unsc.contested(scoped)

    raw = ag.score(unsc.to_vote_table(scoped), "RUS", "CHN")
    cont = ag.score(unsc.to_vote_table(con), "RUS", "CHN")

    assert raw.agreement == pytest.approx(0.950, abs=0.002)
    assert cont.agreement == pytest.approx(0.579, abs=0.002)
    assert cont.opposed == 0                      # never on opposite sides
    assert cont.partial_split == 102

    # and the Western P3 is the tighter bloc on the same ballots
    tbl = unsc.to_vote_table(con)
    assert ag.score(tbl, "GBR", "FRA").agreement > cont.agreement
    assert ag.score(tbl, "USA", "GBR").agreement > cont.agreement


def test_ga_loader_rejects_the_codebook():
    """The uploaded GA markdown is documentation, not the dataset."""
    with pytest.raises(ValueError, match="codebook"):
        ga.load(str(ROOT / "docs" / "reference" / "ga_voting_codebook_v5.md"))


# --------------------------------------------------------------------------- #
# General Assembly export
# --------------------------------------------------------------------------- #

GA_DATA = ROOT / "data" / "raw" / "2026_02_06_ga_voting.csv.gz"
ga_only = pytest.mark.skipif(not GA_DATA.exists(), reason="GA export not present")


@pytest.fixture(scope="module")
def resolutions():
    return ga.load(str(GA_DATA))


@ga_only
def test_ga_session_codes_are_not_plain_integers(resolutions):
    """`4sp` and `11emsp` are special / emergency special sessions.

    The published codebook documents `session` only as "session number". Code
    that calls int() on it crashes; code that filters to digits silently drops
    the emergency special sessions, which is where the Ukraine votes live.
    """
    kinds = {r.session_kind for r in resolutions}
    assert kinds == {"regular", "special", "emergency_special"}

    nonnumeric = [r for r in resolutions if not r.session.isdigit()]
    assert len(nonnumeric) == 74
    assert all(r.session_number is not None for r in nonnumeric)

    es11 = [r for r in resolutions if r.session_kind == "emergency_special"
            and r.session_number == 11]
    assert len(es11) == 9
    assert all(r.session.isdigit() is False for r in es11)


@ga_only
def test_session_sort_key_orders_without_crashing(resolutions):
    codes = sorted({r.session for r in resolutions}, key=ga.session_sort_key)
    assert codes[0] == "1"
    assert ga.session_sort_key("79") < ga.session_sort_key("1sp")
    assert ga.session_sort_key("1sp") < ga.session_sort_key("1emsp")


@ga_only
def test_regular_sessions_excludes_crisis_sessions(resolutions):
    reg = ga.regular_sessions(resolutions)
    assert len(reg) == len(resolutions) - 74
    assert all(r.session_kind == "regular" for r in reg)


@ga_only
def test_ga_headline_results_are_reproducible(resolutions):
    """Guards the GA numbers quoted in docs/03-findings-2026-09.md."""
    scoped = [r for r in resolutions if r.china_seat == "PRC" and r.date >= "1992-01-01"]
    tbl = ga.to_vote_table(scoped)
    con = ag.contested(tbl)

    assert ag.score(tbl, "RUS", "CHN").agreement == pytest.approx(0.711, abs=0.002)
    assert ag.score(con, "RUS", "CHN").agreement == pytest.approx(0.584, abs=0.002)

    # The base-rate control: the dyad is LESS aligned than the Global South mean,
    # and China agrees more with India and Pakistan than with Russia.
    assert ag.mean_pairwise(con, ("DZA", "EGY", "IND", "IDN", "IRN", "PAK", "NGA",
                                 "ZAF", "BRA", "CUB", "VEN", "MYS", "THA", "LKA",
                                 "ZWE")) > ag.score(con, "RUS", "CHN").agreement
    assert ag.score(con, "CHN", "PAK").agreement > ag.score(con, "RUS", "CHN").agreement
    assert ag.score(con, "CHN", "IND").agreement > ag.score(con, "RUS", "CHN").agreement


@ga_only
def test_ukraine_and_palestine_sessions_diverge_sharply(resolutions):
    """Alignment is issue-contingent, not uniform."""
    scoped = [r for r in resolutions if r.china_seat == "PRC" and r.date >= "1992-01-01"]

    def es(num):
        sub = [r for r in scoped if r.session_kind == "emergency_special"
               and r.session_number == num]
        return ag.score(ga.to_vote_table(sub), "RUS", "CHN")

    ukraine, palestine = es(11), es(10)
    assert ukraine.agreement == pytest.approx(0.222, abs=0.002)
    assert palestine.agreement == pytest.approx(0.923, abs=0.002)
    assert palestine.agreement > ukraine.agreement


@ga_only
def test_contested_filter_moves_the_published_trend(resolutions):
    """The reported 2018->2024 decline is mostly an artefact of near-unanimous votes."""
    scoped = ga.regular_sessions(
        [r for r in resolutions if r.china_seat == "PRC" and r.date >= "1992-01-01"]
    )
    sess = ga.sessions(scoped)
    tbl = ga.to_vote_table(scoped)
    con = ag.contested(tbl)

    raw = ag.by_session(tbl, sess, "RUS", "CHN")
    cont = ag.by_session(con, sess, "RUS", "CHN")

    raw_drop = raw["72"].agreement - raw["78"].agreement          # 2018 -> 2024
    con_drop = cont["72"].agreement - cont["78"].agreement
    assert raw_drop > 0.10                                        # ~11 points raw
    assert con_drop < 0.03                                        # ~2 points contested
    assert raw_drop > con_drop * 3


# --------------------------------------------------------------------------- #
# 2021-2026 window (docs/03-findings-2026-09.md section 1.6)
# --------------------------------------------------------------------------- #

WINDOW = "2021-01-01"


@ga_only
def test_window_ga_headline(resolutions):
    scoped = [r for r in resolutions if r.china_seat == "PRC" and r.date >= WINDOW]
    tbl = ga.to_vote_table(scoped)
    con = ag.contested(tbl)

    assert len(scoped) == 550
    assert ag.score(tbl, "RUS", "CHN").agreement == pytest.approx(0.729, abs=0.002)
    assert ag.score(con, "RUS", "CHN").agreement == pytest.approx(0.681, abs=0.002)


@ga_only
def test_window_is_more_aligned_than_the_long_run(resolutions):
    """The recent window points the opposite way to the 'friends moving apart' reading."""
    prc = [r for r in resolutions if r.china_seat == "PRC" and r.date >= "1992-01-01"]
    win = [r for r in prc if r.date >= WINDOW]

    long_run = ag.score(ag.contested(ga.to_vote_table(prc)), "RUS", "CHN").agreement
    recent = ag.score(ag.contested(ga.to_vote_table(win)), "RUS", "CHN").agreement
    assert recent > long_run + 0.08


@ga_only
def test_window_base_rate_still_inverts(resolutions):
    """Alignment rose, but stays below the ambient Global South level."""
    win = [r for r in resolutions if r.china_seat == "PRC" and r.date >= WINDOW]
    con = ag.contested(ga.to_vote_table(win))

    dyad = ag.score(con, "RUS", "CHN").agreement
    g77 = ag.mean_pairwise(con, ("DZA", "EGY", "IND", "IDN", "IRN", "PAK", "NGA",
                                 "ZAF", "BRA", "CUB", "VEN", "MYS", "THA", "LKA", "ZWE"))
    assert g77 == pytest.approx(0.793, abs=0.002)
    assert dyad < g77
    # China-India fell to roughly the Russia-China level in this window
    assert ag.score(con, "CHN", "IND").agreement == pytest.approx(0.668, abs=0.002)


@ga_only
def test_window_russia_is_the_rejectionist(resolutions):
    """Of the contested GA splits, Russia takes the more negative side ~95% of the time."""
    win = [r for r in resolutions if r.china_seat == "PRC" and r.date >= WINDOW]
    con = ag.contested(ga.to_vote_table(win))

    harsher = {"RUS": 0, "CHN": 0}
    for votes in con.values():
        r, c = votes.get("RUS"), votes.get("CHN")
        if r is None or c is None or r == c or ag.ABSENT in (r, c):
            continue
        # higher code = more negative (1 yes, 2 abstain, 3 no)
        harsher["RUS" if r > c else "CHN"] += 1

    assert harsher["RUS"] == 95
    assert harsher["CHN"] == 5


@ga_only
def test_window_opposed_votes_are_arms_control_and_rights(resolutions):
    """31 of 33 opposed votes are Russia no / China yes."""
    win = [r for r in resolutions if r.china_seat == "PRC" and r.date >= WINDOW]
    con = ag.contested(ga.to_vote_table(win))
    opposed = [v for v in con.values() if {v.get("RUS"), v.get("CHN")} == {ag.YES, ag.NO}]

    assert len(opposed) == 33
    assert sum(1 for v in opposed if v["RUS"] == ag.NO) == 31


@ga_only
def test_window_issue_contingency_is_absolute(resolutions):
    """Palestine 100%, Ukraine 22% -- same governments, same five years."""
    win = [r for r in resolutions if r.china_seat == "PRC" and r.date >= WINDOW]

    def es(num):
        sub = [r for r in win if r.session_kind == "emergency_special"
               and r.session_number == num]
        return ag.score(ga.to_vote_table(sub), "RUS", "CHN")

    assert es(10).agreement == 1.0
    assert es(11).agreement == pytest.approx(0.222, abs=0.002)


def test_window_unsc_headline(ballots):
    win = [b for b in ballots if b.date >= WINDOW]
    con = unsc.contested(win)

    assert len(win) == 252
    assert ag.score(unsc.to_vote_table(win), "RUS", "CHN").agreement == pytest.approx(0.889, abs=0.002)
    assert ag.score(unsc.to_vote_table(con), "RUS", "CHN").agreement == pytest.approx(0.636, abs=0.002)


def test_window_unsc_russia_abstains_far_more_than_china(ballots):
    con = unsc.contested([b for b in ballots if b.date >= WINDOW])
    rate = {m: sum(1 for b in con if b.votes.get(m) == ag.ABSTAIN) / len(con)
            for m in ("RUS", "CHN", "USA", "GBR", "FRA")}

    assert rate["RUS"] == pytest.approx(0.81, abs=0.01)
    assert rate["CHN"] == pytest.approx(0.55, abs=0.01)
    assert rate["RUS"] > rate["CHN"] > rate["USA"]


def test_window_unsc_us_russia_alignment_collapses(ballots):
    """The dyad looks tighter partly because the alternatives decayed faster."""
    full = unsc.to_vote_table(unsc.contested(
        [b for b in ballots if b.china_seat == "PRC" and b.date >= unsc.USSR_SUCCESSION]))
    win = unsc.to_vote_table(unsc.contested([b for b in ballots if b.date >= WINDOW]))

    assert ag.score(win, "USA", "RUS").agreement == pytest.approx(0.169, abs=0.002)
    assert ag.score(win, "USA", "RUS").agreement < ag.score(full, "USA", "RUS").agreement
    assert ag.score(win, "GBR", "FRA").agreement > 0.95      # P3 stays cohesive


def test_window_unsc_never_opposed(ballots):
    con = unsc.contested([b for b in ballots if b.date >= WINDOW])
    assert ag.score(unsc.to_vote_table(con), "RUS", "CHN").opposed == 0


# --------------------------------------------------------------------------- #
# Partial splits are partial alignment (docs/03-findings-2026-09.md section 1.0)
# --------------------------------------------------------------------------- #

def test_s_score_credits_partial_alignment():
    """Veto + abstain must not score as total disagreement."""
    table = {
        "identical": {"RUS": ag.NO, "CHN": ag.NO},
        "veto_plus_abstain": {"RUS": ag.NO, "CHN": ag.ABSTAIN},
        "opposed": {"RUS": ag.NO, "CHN": ag.YES},
    }
    r = ag.score(table, "RUS", "CHN")
    assert r.identical == 1 and r.partial_split == 1 and r.opposed == 1
    assert r.agreement == pytest.approx(1 / 3)
    assert r.s_score == pytest.approx(0.5)       # 1 + 0.5 + 0, over 3
    assert r.s_score > r.agreement


def test_s_score_bounds():
    allsame = {"a": {"X": ag.YES, "Y": ag.YES}}
    allopp = {"a": {"X": ag.YES, "Y": ag.NO}}
    assert ag.score(allsame, "X", "Y").s_score == 1.0
    assert ag.score(allopp, "X", "Y").s_score == 0.0


def test_summary_exposes_both_measures():
    d = ag.score({"a": {"X": ag.YES, "Y": ag.ABSTAIN}}, "X", "Y").summary()
    assert d["agreement"] == 0.0 and d["s_score"] == 0.5


def test_mean_pairwise_rejects_mismatched_measure():
    with pytest.raises(ValueError):
        ag.mean_pairwise({}, ["A", "B"], measure="exact")


@ga_only
def test_ukraine_graded_score_is_far_higher_than_exact(resolutions):
    """The figure an earlier draft leaned on understated alignment by 39 points."""
    es11 = [r for r in resolutions
            if r.session_kind == "emergency_special" and r.session_number == 11]
    r = ag.score(ga.to_vote_table(es11), "RUS", "CHN")

    assert r.agreement == pytest.approx(0.222, abs=0.002)
    assert r.s_score == pytest.approx(0.611, abs=0.002)
    assert r.opposed == 0                     # never on opposite sides, even here
    assert r.partial_split == 7


@ga_only
def test_china_never_joined_the_majority_on_ukraine(resolutions):
    es11 = [r for r in resolutions
            if r.session_kind == "emergency_special" and r.session_number == 11]
    prof = ag.withheld_from_majority(ga.to_vote_table(es11), "CHN")

    assert prof["ballots"] == 9
    assert prof["with_majority"] == 0
    assert prof["withheld"] == 7 and prof["against"] == 2


@ga_only
def test_ukraine_abstention_is_common_but_opposition_is_rare(resolutions):
    """The base rate that cuts the finding down: 29 states withheld, only 16 opposed twice."""
    es11 = [r for r in resolutions
            if r.session_kind == "emergency_special" and r.session_number == 11]
    tbl = ga.to_vote_table(es11, china_seat=None, russia_actor="spliced")
    codes = sorted({c for b in tbl.values() for c in b})
    profiles = [ag.withheld_from_majority(tbl, c) for c in codes]
    present = [p for p in profiles if p["ballots"] >= 8]

    never_with_majority = [p for p in present if p["with_majority"] == 0]
    hard_no = [p for p in present if p["against"] >= 2]

    assert len(never_with_majority) == 29          # India among them
    assert "IND" in {p["country"] for p in never_with_majority}
    assert len(hard_no) == 16                      # China among them, India not
    assert {"CHN", "RUS", "BLR", "PRK", "SYR", "IRN"} <= {p["country"] for p in hard_no}
    assert "IND" not in {p["country"] for p in hard_no}


def test_veto_table_codes_veto_plus_abstain_as_partial():
    """The 2022 Ukraine annexation vote: Russia veto, China abstain."""
    import csv
    rows = list(csv.DictReader((ROOT / "data" / "seed" / "unsc_actions.csv").open(encoding="utf-8")))
    by_date = {r["date"]: r for r in rows}

    ukraine = by_date["2022-09-30"]
    assert ukraine["russia_vote"] == "veto" and ukraine["china_vote"] == "abstain"
    assert ukraine["alignment"] == "partial"
    assert ukraine["alignment_basis"] == "one_veto_one_abstain"

    for r in rows:
        if {r["russia_vote"], r["china_vote"]} == {"veto", "abstain"}:
            assert r["alignment"] == "partial", f"{r['date']} miscoded as {r['alignment']}"
        if r["russia_vote"] == "veto" and r["china_vote"] == "veto":
            assert r["alignment"] == "joint"

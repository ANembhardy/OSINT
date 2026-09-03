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

"""Command line entry point.

    python -m rcwatch contacts   [--level leader] [--csv data/seed/meetings.csv]
    python -m rcwatch agreement  --votes votes.csv [--contested] [--baselines]
    python -m rcwatch unsc       [--data ...] [--audit]
    python -m rcwatch ga         [--data ...] [--since 1992-01-01]
    python -m rcwatch gdelt-sql  [--start 2015-01-01]
    python -m rcwatch undl       --query '...' [--limit 25] [--out votes.csv]
    python -m rcwatch audit
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import agreement, events, phrases


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_contacts(args) -> int:
    contacts = events.load(args.csv)
    problems = events.validate(contacts)
    if problems:
        print("data-quality problems:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
    _print(
        {
            "indicators": events.indicators(contacts, args.level),
            "timeline": events.timeline([c for c in contacts if c.level == args.level]),
        }
    )
    return 1 if problems else 0


def cmd_agreement(args) -> int:
    table = agreement.load_votes(args.votes)
    if args.contested:
        table = agreement.contested(table, args.threshold)
    if args.baselines:
        _print(agreement.compare_baselines(table, (args.a, args.b)))
    else:
        res = agreement.score(table, args.a, args.b)
        _print(
            res.summary()
            | {"divergences": [d.__dict__ for d in res.divergences][: args.show]}
        )
    return 0


def cmd_gdelt_sql(args) -> int:
    from . import gdelt

    print(gdelt.bigquery_sql(start=args.start))
    return 0


def cmd_undl(args) -> int:
    from . import undl

    records = undl.search(args.query, limit=args.limit)
    rows = undl.to_long_rows(records)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["rcid", "session", "country", "vote"])
            w.writeheader()
            w.writerows(rows)
        print(f"{len(records)} records, {len(rows)} vote rows -> {args.out}")
    else:
        _print([{"id": r.record_id, "symbol": r.symbol, "title": r.title,
                 "date": r.date, "n_votes": len(r.votes), "url": r.url} for r in records])
    return 0


SC_DEFAULT = "data/raw/2026_02_06_sc_voting.csv.gz"
GA_DEFAULT = "data/raw/2026_02_06_ga_voting.csv.gz"


def cmd_unsc(args) -> int:
    """Russia-China behaviour on adopted Security Council resolutions."""
    from . import unsc

    if args.audit:
        _print(unsc.audit(args.data))
        return 0

    ballots = unsc.load(args.data)
    floor = max(args.since, unsc.USSR_SUCCESSION)
    scoped = [
        b for b in ballots
        if b.china_seat == "PRC" and floor <= b.date < args.until
    ]
    if not scoped:
        print(f"no ballots in {args.since}..{args.until}", file=sys.stderr)
        return 1
    con = unsc.contested(scoped)

    out = {
        "source": args.data,
        "scope_warning": unsc.audit(args.data)["scope_warning"],
        "window": [args.since, args.until],
        "window_actual": [min(b.date for b in scoped), max(b.date for b in scoped)],
        "adopted_ballots": len(ballots),
        "in_scope_prc_post_soviet": len(scoped),
        "contested_ballots": len(con),
        "contested_share": round(len(con) / len(scoped), 4) if scoped else None,
    }

    for label, subset in (("all_adopted", scoped), ("contested_only", con)):
        res = agreement.score(unsc.to_vote_table(subset), args.a, args.b)
        out[label] = res.summary()

    tbl = unsc.to_vote_table(con)
    out["baselines_contested"] = [
        agreement.score(tbl, x, y, keep_divergences=False).summary()
        for x, y in ((args.a, args.b), ("USA", "GBR"), ("USA", "FRA"),
                     ("GBR", "FRA"), ("USA", args.a), ("USA", args.b))
    ]

    # direction of the split, and abstention propensity
    split = {"a_yes_b_abstain": 0, "b_yes_a_abstain": 0, "other": 0}
    for b in con:
        va, vb = b.votes.get(args.a), b.votes.get(args.b)
        if va is None or vb is None or va == vb:
            continue
        if va == agreement.YES and vb == agreement.ABSTAIN:
            split["a_yes_b_abstain"] += 1
        elif vb == agreement.YES and va == agreement.ABSTAIN:
            split["b_yes_a_abstain"] += 1
        else:
            split["other"] += 1
    out["split_direction"] = split
    out["abstention_rate_contested"] = {
        c: round(sum(1 for b in con if b.votes.get(c) == agreement.ABSTAIN) / len(con), 4)
        for c in (args.a, args.b, "USA", "GBR", "FRA")
    } if con else {}

    # Yearly when the observed window is short, five-yearly when it is long.
    # Derived from the data actually in scope, not from the --until default.
    years = [b.year for b in scoped]
    span = max(years) - min(years)
    key = (lambda b: str(b.year)) if span <= 10 else \
          (lambda b: f"{(b.year // 5) * 5}-{(b.year // 5) * 5 + 4}")
    periods: dict[str, list] = {}
    for b in con:
        periods.setdefault(key(b), []).append(b)
    out["by_period_contested"] = {
        k: agreement.score(unsc.to_vote_table(v), args.a, args.b,
                           keep_divergences=False).summary()
        for k, v in sorted(periods.items())
    }

    _print(out)
    return 0


GA_BASELINES = (("RUS", "IND"), ("CHN", "IND"), ("CHN", "BRA"), ("RUS", "IRN"),
                ("CHN", "PAK"), ("CHN", "ZAF"), ("USA", "GBR"), ("FRA", "DEU"))

#: A rough Global South caucus, for the bloc-effect control (measure M2).
G77_SAMPLE = ("DZA", "EGY", "IND", "IDN", "IRN", "PAK", "NGA", "ZAF",
              "BRA", "CUB", "VEN", "MYS", "THA", "LKA", "ZWE")


def cmd_ga(args) -> int:
    """Russia-China behaviour on General Assembly recorded votes."""
    from . import ga

    res = ga.load(args.data)
    scoped = [r for r in res
              if r.china_seat == "PRC" and args.since <= r.date < args.until]
    if not scoped:
        print(f"no resolutions in {args.since}..{args.until}", file=sys.stderr)
        return 1
    regular = ga.regular_sessions(scoped)

    tbl = ga.to_vote_table(scoped)
    con = agreement.contested(tbl, args.threshold)

    out = {
        "source": args.data,
        "citation": ga.CITATION,
        "resolutions_total": len(res),
        "window": [args.since, args.until],
        "window_actual": [min(r.date for r in scoped), max(r.date for r in scoped)],
        "in_scope": len(scoped),
        "contested_ballots": len(con),
        "contested_share": round(len(con) / len(tbl), 4) if tbl else None,
        "session_kinds": {
            k: sum(1 for r in scoped if r.session_kind == k)
            for k in ("regular", "special", "emergency_special")
        },
    }
    for label, t in (("all_recorded", tbl), ("contested_only", con)):
        out[label] = agreement.score(t, args.a, args.b, keep_divergences=False).summary()

    out["baselines_contested"] = [
        agreement.score(con, x, y, keep_divergences=False).summary()
        for x, y in ((args.a, args.b), *GA_BASELINES)
    ]
    out["g77_mean_pairwise_contested"] = round(agreement.mean_pairwise(con, G77_SAMPLE), 4)

    # Per-session trend on regular sessions only.
    sess = ga.sessions(regular)
    reg_tbl = ga.to_vote_table(regular)
    reg_con = agreement.contested(reg_tbl, args.threshold)
    raw_s = agreement.by_session(reg_tbl, sess, args.a, args.b)
    con_s = agreement.by_session(reg_con, sess, args.a, args.b)
    out["by_session_regular"] = {
        s: {
            "raw": raw_s[s].summary()["agreement"],
            "raw_n": raw_s[s].comparable,
            "contested": con_s[s].summary()["agreement"] if s in con_s else None,
            "contested_n": con_s[s].comparable if s in con_s else 0,
        }
        for s in sorted(raw_s, key=ga.session_sort_key)
        if raw_s[s].comparable >= args.min_n
    }

    # Emergency special sessions, broken out: ES-11 is Ukraine, ES-10 Palestine.
    out["emergency_special"] = {}
    for num in sorted({r.session_number for r in scoped
                       if r.session_kind == "emergency_special"}):
        sub = [r for r in scoped
               if r.session_kind == "emergency_special" and r.session_number == num]
        r = agreement.score(ga.to_vote_table(sub), args.a, args.b, keep_divergences=False)
        if r.comparable:
            out["emergency_special"][f"ES-{num}"] = r.summary()

    _print(out)
    return 0


def cmd_audit(args) -> int:
    """Provenance audit: what in the seed data is still unverified?"""
    report = {}
    for name in ("meetings", "joint_documents", "unsc_actions"):
        path = Path("data/seed") / f"{name}.csv"
        if not path.exists():
            continue
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        unverified = [r for r in rows if r.get("verification") != "verified"]
        report[name] = {
            "rows": len(rows),
            "verified": len(rows) - len(unverified),
            "needs_primary_record": [
                r.get("date") or r.get("date_signed") or r.get("title", "?")
                for r in unverified
            ],
        }
    report["markers_tracked"] = len(phrases.MARKERS)
    _print(report)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rcwatch", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("contacts", help="diplomatic contact indicators (M5)")
    c.add_argument("--csv", default="data/seed/meetings.csv")
    c.add_argument("--level", default="leader", choices=events.LEVELS)
    c.set_defaults(func=cmd_contacts)

    a = sub.add_parser("agreement", help="dyadic vote agreement (M1-M3)")
    a.add_argument("--votes", required=True)
    a.add_argument("--a", default="RUS")
    a.add_argument("--b", default="CHN")
    a.add_argument("--contested", action="store_true", help="restrict to contested roll-calls")
    a.add_argument("--threshold", type=float, default=0.10)
    a.add_argument("--baselines", action="store_true", help="include control dyads (M2)")
    a.add_argument("--show", type=int, default=20, help="max divergences to print")
    a.set_defaults(func=cmd_agreement)

    g = sub.add_parser("gdelt-sql", help="emit BigQuery SQL for the contact series")
    g.add_argument("--start", default="2015-01-01")
    g.set_defaults(func=cmd_gdelt_sql)

    u = sub.add_parser("undl", help="query the UN Digital Library for voting records")
    u.add_argument("--query", required=True)
    u.add_argument("--limit", type=int, default=25)
    u.add_argument("--out")
    u.set_defaults(func=cmd_undl)

    n = sub.add_parser("unsc", help="Russia-China behaviour on adopted Security Council resolutions")
    n.add_argument("--data", default=SC_DEFAULT)
    n.add_argument("--a", default="RUS")
    n.add_argument("--b", default="CHN")
    n.add_argument("--since", default="1992-01-01", help="ISO date, inclusive")
    n.add_argument("--until", default="2100-01-01", help="ISO date, exclusive")
    n.add_argument("--audit", action="store_true", help="print the data-quality report only")
    n.set_defaults(func=cmd_unsc)

    g2 = sub.add_parser("ga", help="Russia-China behaviour on General Assembly recorded votes")
    g2.add_argument("--data", default=GA_DEFAULT)
    g2.add_argument("--a", default="RUS")
    g2.add_argument("--b", default="CHN")
    g2.add_argument("--since", default="1992-01-01", help="ISO date; default skips the Soviet series")
    g2.add_argument("--until", default="2100-01-01", help="ISO date, exclusive")
    g2.add_argument("--threshold", type=float, default=0.10)
    g2.add_argument("--min-n", type=int, default=10, help="drop sessions with fewer comparable votes")
    g2.set_defaults(func=cmd_ga)

    d = sub.add_parser("audit", help="provenance audit of the seed data")
    d.set_defaults(func=cmd_audit)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

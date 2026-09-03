"""Command line entry point.

    python -m rcwatch contacts   [--level leader] [--csv data/seed/meetings.csv]
    python -m rcwatch agreement  --votes votes.csv [--contested] [--baselines]
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

    d = sub.add_parser("audit", help="provenance audit of the seed data")
    d.set_defaults(func=cmd_audit)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

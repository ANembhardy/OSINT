"""GDELT 2.0 access for dyadic contact intensity (measure M5).

Two routes:

* `doc_volume` -- the DOC 2.0 API, no key required, good for a quick tempo series.
* `bigquery_sql` -- emits the SQL for `gdelt-bq.gdeltv2.events`, which is the
  route you actually want for analysis. GDELT's full event table is not
  practically queryable over HTTP.

CAMEO root codes that matter for diplomatic coordination:
    03  intent to cooperate       04  consult
    05  diplomatic cooperation    06  material cooperation
"""

from __future__ import annotations

from .http import get_json

DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

COOPERATION_ROOTS = ("03", "04", "05", "06")


def doc_volume(query: str, *, timespan: str = "12months", mode: str = "timelinevolinfo") -> dict:
    """Media-volume time series for a query. Proxy for tempo, not ground truth."""
    return get_json(DOC_API, params={"query": query, "mode": mode, "timespan": timespan, "format": "json"})


def bigquery_sql(
    actor_a: str = "RUS",
    actor_b: str = "CHN",
    start: str = "2015-01-01",
    roots: tuple[str, ...] = COOPERATION_ROOTS,
) -> str:
    """SQL for a deduplicated monthly contact series between two state actors.

    Deduplication matters: GDELT emits one event row per source article, so raw
    counts measure press attention as much as diplomatic activity. Collapsing to
    distinct (day, actor pair, event code) triples is the minimum correction.
    """
    root_list = ", ".join(f"'{r}'" for r in roots)
    return f"""
-- Monthly Russia-China cooperative-contact events, deduplicated.
WITH e AS (
  SELECT DISTINCT
    DATE(PARSE_TIMESTAMP('%Y%m%d', CAST(SQLDATE AS STRING))) AS day,
    EventRootCode,
    EventCode,
    Actor1CountryCode,
    Actor2CountryCode,
    AvgTone,
    GoldsteinScale
  FROM `gdelt-bq.gdeltv2.events`
  WHERE SQLDATE >= {start.replace('-', '')}
    AND EventRootCode IN ({root_list})
    AND (
      (Actor1CountryCode = '{actor_a}' AND Actor2CountryCode = '{actor_b}') OR
      (Actor1CountryCode = '{actor_b}' AND Actor2CountryCode = '{actor_a}')
    )
)
SELECT
  FORMAT_DATE('%Y-%m', day)      AS month,
  EventRootCode,
  COUNT(*)                       AS events,
  ROUND(AVG(GoldsteinScale), 3)  AS mean_goldstein,
  ROUND(AVG(AvgTone), 3)         AS mean_tone
FROM e
GROUP BY month, EventRootCode
ORDER BY month, EventRootCode;
""".strip()

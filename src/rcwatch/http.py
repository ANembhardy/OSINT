"""Minimal polite HTTP layer: stdlib only, on-disk cache, explicit provenance.

Every fetch writes a sidecar `.meta.json` recording the URL and retrieval time,
so any downstream claim can be traced to a specific retrieval.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "rcwatch/0.1 (open-source research; contact via repository)"
CACHE_DIR = Path("out/cache")
MIN_INTERVAL = 1.0          # seconds between requests to the same host

_last_hit: dict[str, float] = {}


def _throttle(host: str) -> None:
    gap = time.monotonic() - _last_hit.get(host, 0.0)
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_hit[host] = time.monotonic()


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:20]


def get(url: str, *, params: dict | None = None, cache: bool = True, timeout: int = 45) -> str:
    """Fetch a URL as text, caching the body and its provenance under out/cache."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    body_path = CACHE_DIR / f"{cache_key(url)}.body"
    meta_path = CACHE_DIR / f"{cache_key(url)}.meta.json"

    if cache and body_path.exists():
        return body_path.read_text(encoding="utf-8")

    _throttle(urllib.parse.urlparse(url).netloc)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")
        status = resp.status

    body_path.write_text(text, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "url": url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "bytes": len(text),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return text


def get_json(url: str, **kw) -> dict | list:
    return json.loads(get(url, **kw))

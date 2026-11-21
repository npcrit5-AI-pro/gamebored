"""Bored Wondering: keyless web search for GameBored (stdlib only).

Three free search sources that need no API key or signup, verified live:

1. DuckDuckGo Instant Answer API - https://api.duckduckgo.com/
2. Wikipedia/MediaWiki search API - https://en.wikipedia.org/w/api.php
3. HN Algolia front-page search API - https://hn.algolia.com/api/v1/search

Only this module touches the network (urllib). Everything else in
GameBored - word lists, scores, games - stays offline.
"""

import html
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = "GameBored/1.3.0 (educational terminal search)"
TIMEOUT = 4

SOURCES = ("duckduckgo", "wikipedia", "hackernews")


MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # never buffer more than 2 MiB per source


def _fetch_json(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1).decode("utf-8", "replace")
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("response too large - skipping")
    return json.loads(raw)


def _clean(text, limit=220):
    if text is None:
        return ""
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return ""
    text = html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def search_duckduckgo(query, timeout=TIMEOUT):
    """DuckDuckGo Instant Answer: abstract + related topics."""
    results = []
    params = urllib.parse.urlencode({
        "q": query, "format": "json", "no_html": 1,
        "skip_disambig": 1, "t": "gamebored",
    })
    data = _fetch_json("https://api.duckduckgo.com/?" + params,
                       timeout=timeout)
    abstract = _clean(data.get("AbstractText") or "")
    url = (data.get("AbstractURL") or "").strip()
    if abstract and url:
        results.append({
            "title": data.get("Heading") or query,
            "source": "duckduckgo",
            "snippet": abstract,
            "url": url,
        })
    for topic in data.get("RelatedTopics") or []:
        if not isinstance(topic, dict):
            continue
        if "Topics" in topic:  # grouped related topics
            for sub in topic["Topics"][:3]:
                if isinstance(sub, dict) and sub.get("Text") and sub.get("FirstURL"):
                    results.append({
                        "title": _clean(sub["Text"], 80),
                        "source": "duckduckgo",
                        "snippet": _clean(sub["Text"]),
                        "url": sub["FirstURL"],
                    })
        elif topic.get("Text") and topic.get("FirstURL"):
            results.append({
                "title": _clean(topic["Text"], 80),
                "source": "duckduckgo",
                "snippet": _clean(topic["Text"]),
                "url": topic["FirstURL"],
            })
        if len(results) >= 6:
            break
    return results[:6]


def search_wikipedia(query, timeout=TIMEOUT):
    """Wikipedia full-text search via the MediaWiki API."""
    results = []
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "utf8": 1, "srlimit": 8,
    })
    data = _fetch_json("https://en.wikipedia.org/w/api.php?" + params,
                       timeout=timeout)
    for item in (data.get("query") or {}).get("search") or []:
        title = item.get("title") or query
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(
            title.replace(" ", "_"))
        results.append({
            "title": title,
            "source": "wikipedia",
            "snippet": _clean(item.get("snippet") or ""),
            "url": url,
        })
    return results[:8]


def search_hackernews(query, timeout=TIMEOUT):
    """Hacker News search via the free Algolia HN API."""
    results = []
    params = urllib.parse.urlencode({"query": query, "hitsPerPage": 8})
    data = _fetch_json("https://hn.algolia.com/api/v1/search?" + params,
                       timeout=timeout)
    for hit in data.get("hits") or []:
        title = hit.get("title") or hit.get("story_title") or ""
        if not title:
            continue
        url = (hit.get("url") or hit.get("story_url")
               or "https://news.ycombinator.com/item?id=%s" % hit.get("objectID", ""))
        snippet = _clean(hit.get("story_text") or hit.get("comment_text")
                         or hit.get("_highlightResult", {}).get("title", {}).get("value", "")
                         or "")
        author = hit.get("author") or "hn"
        results.append({
            "title": _clean(title, 80),
            "source": "hackernews",
            "snippet": snippet or ("by %s - %d points" % (
                author, hit.get("points") or 0)),
            "url": url,
        })
    return results[:8]


_SEARCHERS = {
    "duckduckgo": search_duckduckgo,
    "wikipedia": search_wikipedia,
    "hackernews": search_hackernews,
}


def _norm_url(url):
    if not isinstance(url, str):
        try:
            url = str(url)
        except Exception:
            return ""
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
    return u


def _as_text(value):
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return ""


def merge_results(per_source):
    """Merge per-source lists: keep order wiki->ddg->hn, dedupe by URL/title.

    Never raises: skips malformed items so one bad source (or injected
    test searcher) cannot take down the results screen.
    """
    seen_urls, seen_titles, merged = set(), set(), []
    if not isinstance(per_source, dict):
        return []
    for source in ("wikipedia", "duckduckgo", "hackernews"):
        items = per_source.get(source, []) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = _as_text(item.get("title") or "").strip()
            url = _as_text(item.get("url") or "").strip()
            if not title or not url:
                continue
            key_u, key_t = _norm_url(url), title.lower()
            if key_u in seen_urls or key_t in seen_titles:
                continue
            seen_urls.add(key_u)
            seen_titles.add(key_t)
            merged.append({
                "title": title,
                "source": item.get("source") or source,
                "snippet": _as_text(item.get("snippet") or ""),
                "url": url,
            })
    return merged


def search_all(query, timeout=TIMEOUT, searchers=None):
    """Query all sources in parallel. Never raises for source failures.

    Returns (results, errors): merged/deduped results and
    {source: friendly error} for sources that failed.
    """
    query = (query or "").strip()
    if not query:
        return [], {}
    funcs = searchers or _SEARCHERS
    per_source, errors = {}, {}

    def _run(name_fn):
        name, fn = name_fn
        try:
            return name, list(fn(query, timeout=timeout) or []), ""
        except Exception as exc:  # offline, timeout, bad JSON: stay friendly
            return name, [], _friendly_error(exc)

    with ThreadPoolExecutor(max_workers=max(1, len(funcs))) as pool:
        for name, items, err in pool.map(_run, list(funcs.items())):
            per_source[name] = items
            if err:
                errors[name] = err
    return merge_results(per_source), errors


def _friendly_error(exc):
    msg = str(exc).lower()
    if "timed out" in msg or "timeout" in msg:
        return "timed out - skipping"
    if "urlopen" in msg or "nodename" in msg or "network" in msg \
            or "unreachable" in msg or "connection" in msg:
        return "no connection - skipping"
    return "unavailable - skipping"

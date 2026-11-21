"""Bored Wondering: keyless web search for GameBored (stdlib only).

Free search sources that need no API key or signup, verified live:

1. DuckDuckGo Instant Answer API - https://api.duckduckgo.com/
2. Wikipedia/MediaWiki search API - https://en.wikipedia.org/w/api.php
3. HN Algolia front-page search API - https://hn.algolia.com/api/v1/search
4. Wiktionary/MediaWiki search API - https://en.wiktionary.org/w/api.php
5. Open Library search API - https://openlibrary.org/search.json

Only this module touches the network (urllib). Everything else in
GameBored - word lists, scores, games - stays offline.
"""

import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor


USER_AGENT = "GameBored/1.5.0 (educational terminal search)"
TIMEOUT = 4
FULL_TIMEOUT = 6

SOURCES = ("wikipedia", "duckduckgo", "hackernews", "wiktionary",
           "openlibrary")

SOURCE_LABELS = {
    "wikipedia": "Wiki",
    "duckduckgo": "DDG",
    "hackernews": "HN",
    "wiktionary": "Dict",
    "openlibrary": "Books",
}

MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # never buffer more than 2 MiB per source
QUERY_CACHE_TTL = 600  # cached query results stay fresh for 10 minutes
FULL_CACHE_LIMIT = 50  # full-article cache holds the last 50 opens

_full_cache = {}


def _fetch_json(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1).decode("utf-8", "replace")
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("response too large - skipping")
    return json.loads(raw)


def _clean(text, limit=900):
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


def plain_text(html_text, limit=200000):
    """Strip tags/entities from HTML into long plain text (for articles)."""
    if html_text is None:
        return ""
    if not isinstance(html_text, str):
        try:
            html_text = str(html_text)
        except Exception:
            return ""
    text = html.unescape(html_text)
    text = re.sub(r"(?i)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|blockquote)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = []
    for raw_line in text.split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    text = "\n".join(lines)
    if limit and len(text) > limit:
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
    infobox = _infobox_facts(data.get("Infobox"))
    related = []
    for topic in data.get("RelatedTopics") or []:
        if not isinstance(topic, dict):
            continue
        if "Topics" in topic:  # grouped related topics
            for sub in topic["Topics"] or []:
                if isinstance(sub, dict) and sub.get("Text") \
                        and sub.get("FirstURL"):
                    related.append((_clean(sub["Text"]),
                                    sub["FirstURL"]))
        elif topic.get("Text") and topic.get("FirstURL"):
            related.append((_clean(topic["Text"]), topic["FirstURL"]))
    if abstract and url:
        meta = {"heading": _clean(data.get("Heading") or query, 120)}
        if infobox:
            meta["infobox"] = infobox
        if related:
            meta["related"] = [{"title": _clean(t, 100), "url": u}
                               for t, u in related[:10]]
        results.append({
            "title": data.get("Heading") or query,
            "source": "duckduckgo",
            "snippet": abstract,
            "url": url,
            "meta": meta,
        })
    for text, link in related:
        results.append({
            "title": _clean(text, 100),
            "source": "duckduckgo",
            "snippet": text,
            "url": link,
        })
        if len(results) >= 8:
            break
    return results[:8]


def _infobox_facts(infobox):
    """Flatten a DDG Infobox payload into 'label: value' fact lines."""
    facts = []
    try:
        content = (infobox or {}).get("content") or []
    except AttributeError:
        return facts
    for block in content:
        if not isinstance(block, dict):
            continue
        label = _clean(block.get("label") or block.get("data_type") or "",
                       60)
        value = block.get("value")
        if isinstance(value, list):
            bits = [_clean(v.get("label") or v.get("value") or "", 80)
                    if isinstance(v, dict) else _clean(v, 80)
                    for v in value]
            value = ", ".join(b for b in bits if b)
        else:
            value = _clean(value, 160)
        if label and value:
            facts.append("%s: %s" % (label, value))
        elif value:
            facts.append(value)
        if len(facts) >= 12:
            break
    return facts


def search_wikipedia(query, timeout=TIMEOUT):
    """Wikipedia full-text search via the MediaWiki API."""
    results = []
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "utf8": 1, "srlimit": 12,
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
            "meta": {"page": title},
        })
    return results[:12]


def search_hackernews(query, timeout=TIMEOUT):
    """Hacker News search via the free Algolia HN API."""
    results = []
    params = urllib.parse.urlencode({"query": query, "hitsPerPage": 12})
    data = _fetch_json("https://hn.algolia.com/api/v1/search?" + params,
                       timeout=timeout)
    for hit in data.get("hits") or []:
        title = hit.get("title") or hit.get("story_title") or ""
        if not title:
            continue
        url = (hit.get("url") or hit.get("story_url")
               or "https://news.ycombinator.com/item?id=%s" % hit.get("objectID", ""))
        snippet = _clean(hit.get("story_text") or hit.get("comment_text")
                         or hit.get("title") or "")
        author = hit.get("author") or "hn"
        points = hit.get("points") or 0
        if not snippet:
            snippet = "by %s - %d points" % (author, points)
        else:
            snippet = "%s (by %s, %d points)" % (snippet, author, points)
        results.append({
            "title": _clean(title, 120),
            "source": "hackernews",
            "snippet": snippet,
            "url": url,
            "meta": {"objectID": hit.get("objectID"),
                     "author": author, "points": points,
                     "comments": hit.get("num_comments") or 0},
        })
    return results[:12]


def search_wiktionary(query, timeout=TIMEOUT):
    """Wiktionary definitions via the MediaWiki API (keyless)."""
    results = []
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "utf8": 1, "srlimit": 6, "srnamespace": 0,
    })
    data = _fetch_json("https://en.wiktionary.org/w/api.php?" + params,
                       timeout=timeout)
    for item in (data.get("query") or {}).get("search") or []:
        title = item.get("title") or query
        url = "https://en.wiktionary.org/wiki/" + urllib.parse.quote(
            title.replace(" ", "_"))
        results.append({
            "title": title,
            "source": "wiktionary",
            "snippet": _clean(item.get("snippet") or ""),
            "url": url,
            "meta": {"page": title},
        })
    return results[:6]


def search_openlibrary(query, timeout=TIMEOUT):
    """Open Library book search (keyless JSON API)."""
    results = []
    params = urllib.parse.urlencode({
        "q": query, "limit": 6,
        "fields": "key,title,author_name,first_publish_year,subject",
    })
    data = _fetch_json("https://openlibrary.org/search.json?" + params,
                       timeout=timeout)
    for doc in data.get("docs") or []:
        if not isinstance(doc, dict):
            continue
        title = doc.get("title") or ""
        key = doc.get("key") or ""
        if not title or not key:
            continue
        authors = ", ".join(doc.get("author_name") or []) or "unknown author"
        year = doc.get("first_publish_year") or "?"
        subjects = ", ".join((doc.get("subject") or [])[:4])
        snippet = "%s (%s). %s" % (title, year, authors)
        if subjects:
            snippet += " - %s" % subjects
        results.append({
            "title": _clean("%s - %s" % (title, authors), 120),
            "source": "openlibrary",
            "snippet": _clean(snippet),
            "url": "https://openlibrary.org" + key,
            "meta": {"key": key, "year": year},
        })
    return results[:6]


_SEARCHERS = {
    "duckduckgo": search_duckduckgo,
    "wikipedia": search_wikipedia,
    "hackernews": search_hackernews,
    "wiktionary": search_wiktionary,
    "openlibrary": search_openlibrary,
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
    """Merge per-source lists: keep source order, dedupe by URL/title.

    Never raises: skips malformed items so one bad source (or injected
    test searcher) cannot take down the results screen. Extra per-result
    metadata ("meta") rides along untouched.
    """
    seen_urls, seen_titles, merged = set(), set(), []
    if not isinstance(per_source, dict):
        return []
    order = [s for s in SOURCES if s in per_source]
    order += [s for s in per_source if s not in order]
    for source in order:
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
            if isinstance(item.get("meta"), dict):
                merged[-1]["meta"] = item["meta"]
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


def search_all_cached(query, timeout=TIMEOUT, searchers=None, cache=None,
                      max_age=QUERY_CACHE_TTL, now=None):
    """search_all plus an in-memory/persisted cache of recent queries.

    cache is a plain dict {query: {"results", "errors", "at"}}; callers may
    persist it between sessions. Returns (results, errors, from_cache).
    """
    query = (query or "").strip()
    if not query:
        return [], {}, False
    stamp = time.time() if now is None else now
    if isinstance(cache, dict):
        entry = cache.get(query.lower())
        if isinstance(entry, dict):
            try:
                age = float(stamp) - float(entry.get("at", 0))
            except (TypeError, ValueError):
                age = max_age + 1
            if 0 <= age <= max_age and isinstance(entry.get("results"),
                                                  list):
                errors = entry.get("errors")
                return (entry["results"],
                        errors if isinstance(errors, dict) else {},
                        True)
    results, errors = search_all(query, timeout=timeout, searchers=searchers)
    if isinstance(cache, dict):
        try:
            cache[query.lower()] = {"results": results, "errors": errors,
                                    "at": stamp}
            while len(cache) > 40:
                oldest = min(cache,
                             key=lambda k: cache[k].get("at", 0)
                             if isinstance(cache[k], dict) else 0)
                del cache[oldest]
        except Exception:
            pass
    return results, errors, False


def prune_cache(cache, max_age=QUERY_CACHE_TTL, now=None):
    """Drop cache entries older than max_age. Returns the cache."""
    if not isinstance(cache, dict):
        return {}
    stamp = time.time() if now is None else now
    for key in list(cache.keys()):
        entry = cache.get(key)
        try:
            age = float(stamp) - float(entry.get("at", 0))
        except (TypeError, ValueError, AttributeError):
            age = max_age + 1
        if age < 0 or age > max_age:
            try:
                del cache[key]
            except KeyError:
                pass
    return cache


def _wiki_extract_api(title, host="en.wikipedia.org", timeout=FULL_TIMEOUT):
    params = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": 1,
        "exsectionformat": "plain", "titles": title, "format": "json",
        "utf8": 1, "redirects": 1,
    })
    data = _fetch_json("https://%s/w/api.php?%s" % (host, params),
                       timeout=timeout)
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        if isinstance(page, dict) and page.get("extract"):
            return page["extract"]
    return ""


def _page_title_from_url(url, host_part="wikipedia.org"):
    try:
        path = urllib.parse.urlparse(url or "").path
        slug = path.rsplit("/wiki/", 1)[-1]
        title = urllib.parse.unquote(slug).replace("_", " ").strip()
        if title and host_part in (url or ""):
            return title
    except Exception:
        pass
    return ""


def fetch_wikipedia_full(result, timeout=FULL_TIMEOUT):
    """Full article plain text with section headings."""
    meta = result.get("meta") if isinstance(result, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    title = meta.get("page") or result.get("title") or ""
    if not title:
        title = _page_title_from_url(result.get("url") or "")
    if not title:
        return {"error": "no article title found"}
    try:
        extract = _wiki_extract_api(title, timeout=timeout)
    except Exception as exc:
        return {"error": _friendly_error(exc)}
    if not extract.strip():
        return {"error": "article came back empty - try the link"}
    return {"title": result.get("title") or title,
            "source": "wikipedia",
            "url": result.get("url") or "",
            "body": plain_text(extract)}


def fetch_wiktionary_full(result, timeout=FULL_TIMEOUT):
    """Full dictionary entry as plain text."""
    meta = result.get("meta") if isinstance(result, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    title = meta.get("page") or result.get("title") or ""
    if not title:
        title = _page_title_from_url(result.get("url") or "",
                                     host_part="wiktionary.org")
    if not title:
        return {"error": "no entry title found"}
    try:
        extract = _wiki_extract_api(title, host="en.wiktionary.org",
                                    timeout=timeout)
    except Exception as exc:
        return {"error": _friendly_error(exc)}
    if not extract.strip():
        return {"error": "entry came back empty - try the link"}
    return {"title": result.get("title") or title,
            "source": "wiktionary",
            "url": result.get("url") or "",
            "body": plain_text(extract)}


def fetch_hn_full(result, timeout=FULL_TIMEOUT):
    """Full HN story text plus top comments via the Algolia items API."""
    meta = result.get("meta") if isinstance(result, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    object_id = meta.get("objectID")
    if object_id is None:
        url = result.get("url") or ""
        match = re.search(r"id=(\d+)", url)
        object_id = match.group(1) if match else None
    if object_id is None:
        return {"error": "no HN item id found"}
    try:
        data = _fetch_json(
            "https://hn.algolia.com/api/v1/items/%s" % object_id,
            timeout=timeout)
    except Exception as exc:
        return {"error": _friendly_error(exc)}
    bits = []
    title = data.get("title") or result.get("title") or "Hacker News"
    bits.append(title.upper())
    bits.append("")
    author = data.get("author") or meta.get("author") or "hn"
    points = data.get("points") if data.get("points") is not None \
        else meta.get("points", 0)
    bits.append("by %s - %s points - %s comments" % (
        author, points, data.get("children") and len(data.get("children"))
        or meta.get("comments", 0)))
    story_text = plain_text(data.get("text") or "")
    if story_text:
        bits += ["", "STORY", story_text]
    comments = _flatten_comments(data.get("children") or [], depth=0,
                                 limit=12)
    if comments:
        bits += ["", "TOP COMMENTS"] + comments
    link = data.get("url") or result.get("url") or ""
    if link:
        bits += ["", "LINK", link]
    return {"title": result.get("title") or title,
            "source": "hackernews",
            "url": result.get("url") or "",
            "body": "\n".join(bits)}


def _flatten_comments(children, depth=0, limit=12):
    out = []
    for child in children or []:
        if len(out) >= limit * 2:
            break
        if not isinstance(child, dict):
            continue
        text = plain_text(child.get("text") or "", limit=600)
        if text:
            prefix = "  " * min(depth, 2)
            author = child.get("author") or "hn"
            out.append("%s%s says: %s" % (prefix, author, text))
            out.append("")
        if depth < 1:
            out += _flatten_comments(child.get("children") or [],
                                     depth=depth + 1, limit=limit)
    return out[: limit * 2]


def fetch_duckduckgo_full(result, timeout=FULL_TIMEOUT):
    """Full DDG instant answer: abstract, facts, and related topics."""
    meta = result.get("meta") if isinstance(result, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    bits = []
    heading = meta.get("heading") or result.get("title") or ""
    if heading:
        bits += [str(heading).upper(), ""]
    snippet = result.get("snippet") or ""
    if snippet:
        bits += ["ANSWER", snippet, ""]
    facts = meta.get("infobox") or []
    if facts:
        bits.append("FACTS")
        bits += ["- %s" % fact for fact in facts[:12]]
        bits.append("")
    related = meta.get("related") or []
    if related:
        bits.append("RELATED TOPICS")
        for item in related[:10]:
            if isinstance(item, dict) and item.get("title"):
                bits.append("- %s" % item["title"])
                if item.get("url"):
                    bits.append("  %s" % item["url"])
        bits.append("")
    url = result.get("url") or ""
    if url:
        bits += ["LINK", url]
    if len(bits) <= 2:
        # No abstract cached: re-fetch the instant answer live.
        try:
            fresh = search_duckduckgo(
                result.get("title") or "", timeout=timeout)
        except Exception as exc:
            return {"error": _friendly_error(exc)}
        if fresh:
            first = fresh[0]
            return fetch_duckduckgo_full(first, timeout=timeout)
        return {"error": "no instant answer for this one"}
    return {"title": result.get("title") or heading,
            "source": "duckduckgo",
            "url": url,
            "body": "\n".join(bits)}


def fetch_openlibrary_full(result, timeout=FULL_TIMEOUT):
    """Full book record: description, subjects, publish info."""
    meta = result.get("meta") if isinstance(result, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    key = meta.get("key")
    if not key:
        try:
            path = urllib.parse.urlparse(result.get("url") or "").path
            if path.startswith("/works/") or path.startswith("/books/"):
                key = path
        except Exception:
            key = None
    if not key:
        return {"error": "no book record found"}
    try:
        data = _fetch_json("https://openlibrary.org%s.json" % key,
                           timeout=timeout)
    except Exception as exc:
        return {"error": _friendly_error(exc)}
    bits = []
    title = data.get("title") or result.get("title") or "Book"
    bits += [str(title).upper(), ""]
    desc = data.get("description")
    if isinstance(desc, dict):
        desc = desc.get("value")
    desc = plain_text(desc or "")
    if desc:
        bits += ["DESCRIPTION", desc, ""]
    first = data.get("first_sentence")
    if isinstance(first, dict):
        first = first.get("value")
    first = plain_text(first or "")
    if first:
        bits += ["FIRST LINE", first, ""]
    subjects = data.get("subjects") or []
    if subjects:
        bits += ["SUBJECTS", ", ".join(subjects[:12]), ""]
    year = meta.get("year")
    if year:
        bits += ["FIRST PUBLISHED", str(year), ""]
    url = result.get("url") or ("https://openlibrary.org" + key)
    bits += ["LINK", url]
    return {"title": result.get("title") or title,
            "source": "openlibrary",
            "url": url,
            "body": "\n".join(bits)}


_FULL_FETCHERS = {
    "wikipedia": fetch_wikipedia_full,
    "wiktionary": fetch_wiktionary_full,
    "hackernews": fetch_hn_full,
    "duckduckgo": fetch_duckduckgo_full,
    "openlibrary": fetch_openlibrary_full,
}


def fetch_full(result, timeout=FULL_TIMEOUT):
    """Full readable content for a result (cached). Never raises.

    Returns {"title", "source", "url", "body"} or {"error": ...}.
    """
    if not isinstance(result, dict):
        return {"error": "nothing to open"}
    url = result.get("url") or ""
    source = result.get("source") or ""
    key = (source, url)
    if key in _full_cache:
        return _full_cache[key]
    fetcher = _FULL_FETCHERS.get(source)
    if fetcher is None:
        # Generic sources: the snippet plus the link is all we have.
        snippet = plain_text(result.get("snippet") or "")
        body = snippet + ("\n\nLINK\n%s" % url if url else "")
        doc = {"title": result.get("title") or url,
               "source": source, "url": url, "body": body or "No text."}
        _remember_full(key, doc)
        return doc
    try:
        doc = fetcher(result, timeout=timeout)
    except Exception as exc:  # stay friendly no matter what
        doc = {"error": _friendly_error(exc)}
    _remember_full(key, doc)
    return doc


def _remember_full(key, doc):
    try:
        _full_cache[key] = doc
        while len(_full_cache) > FULL_CACHE_LIMIT:
            _full_cache.pop(next(iter(_full_cache)))
    except Exception:
        pass


def clear_caches():
    _full_cache.clear()


def _friendly_error(exc):
    msg = str(exc).lower()
    if "timed out" in msg or "timeout" in msg:
        return "timed out - skipping"
    if "urlopen" in msg or "nodename" in msg or "network" in msg \
            or "unreachable" in msg or "connection" in msg:
        return "no connection - skipping"
    return "unavailable - skipping"

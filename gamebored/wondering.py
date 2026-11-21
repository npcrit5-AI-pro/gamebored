"""Bored Wondering UI: search, browse, and actually read the results.

Type a query, browse merged results with long wrapped summaries, pick a
source tab (All/Wiki/HN/DDG/Dict/Books), and open any result in a
full-screen reader: the complete Wikipedia article, the HN story plus top
comments, the full instant answer, book details. '/' finds text inside the
reader, 'n' jumps to the next result.
"""

import curses
import time
from concurrent.futures import ThreadPoolExecutor

from . import scores as scores_mod
from . import search as search_mod
from . import storage as storage_mod
from . import ui

TITLE = "Bored Wondering"
DESCRIPTION = "Search the web, keyless"
CONTROLS = ("Type + Enter search | Up/Down pick | Left/Right source tab | "
            "Enter read | q menu")
GAME_ID = "wondering"
CATEGORY = "Explore"

SOURCE_COLORS = {"wikipedia": 1, "duckduckgo": 4, "hackernews": 3,
                 "wiktionary": 2, "openlibrary": 6}

HISTORY_KEY = "_wonder_history"
CACHE_NAME = "wonder_cache.json"
CACHE_LIMIT = 20

TABS = ["all", "wikipedia", "duckduckgo", "hackernews", "wiktionary",
        "openlibrary"]

TAB_LABELS = {"all": "All", "wikipedia": "Wiki", "duckduckgo": "DDG",
              "hackernews": "HN", "wiktionary": "Dict",
              "openlibrary": "Books"}


def get_history(score_store):
    items = score_store.get(HISTORY_KEY)
    return list(items) if isinstance(items, list) else []


def add_history(score_store, query):
    query = (query or "").strip()
    if not query:
        return
    hist = [q for q in get_history(score_store) if q.lower() != query.lower()]
    hist.insert(0, query)
    score_store[HISTORY_KEY] = hist[:20]
    try:
        scores_mod.save(score_store)
    except Exception:
        pass


def load_query_cache(path=None):
    raw = storage_mod.load_json(CACHE_NAME, {},
                                path=path or storage_mod.data_path(CACHE_NAME))
    if not isinstance(raw, dict):
        return {}
    return search_mod.prune_cache(raw)


def save_query_cache(cache, path=None):
    try:
        trimmed = dict(list(cache.items())[-CACHE_LIMIT:])
    except Exception:
        trimmed = {}
    storage_mod.save_json(CACHE_NAME, trimmed,
                          path=path or storage_mod.data_path(CACHE_NAME))


def filter_by_tab(results, tab):
    if tab == "all":
        return list(results or [])
    return [r for r in (results or []) if r.get("source") == tab]


def wrap_text(text, width):
    """Word-wrap plain text to width, keeping blank lines. Never raises."""
    try:
        width = max(20, int(width))
    except (TypeError, ValueError):
        width = 70
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return []
    out = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            if not word:
                continue
            if len(cur) + len(word) + 1 > width:
                if cur:
                    out.append(cur)
                while len(word) > width:
                    out.append(word[:width])
                    word = word[width:]
                cur = word
            else:
                cur = (cur + " " + word).strip()
        out.append(cur)
    return out


def wrap_snippet(text, width, max_lines=3):
    """Wrap a result summary to at most max_lines display lines."""
    lines = wrap_text(text or "(no summary)", width)
    lines = [ln for ln in lines if ln][:max_lines] or [""]
    return lines


def _visible_rows(win):
    try:
        h, _ = win.getmaxyx()
        return max(1, (h - 8) // 3)
    except curses.error:
        return 4


def results_per_page(win):
    """How many multi-line results fit on screen."""
    try:
        h, _ = win.getmaxyx()
        return max(1, (h - 10) // 5)
    except curses.error:
        return 2


def draw_screen(win, query, results, errors, sel, top, searching,
                last_query, tab="all", from_cache=False):
    try:
        win.clear()
    except curses.error:
        pass
    h, w = win.getmaxyx()
    ui.header(win, "BORED WONDERING", "the keyless corner of the internet")
    ui.safe_addstr(win, 2, 2, "Ask: " + (query + "_")[: max(0, w - 8)],
                   curses.A_BOLD | ui.color(3))
    # source tabs
    tab_x = 2
    for key in TABS:
        label = " %s " % TAB_LABELS[key]
        attr = ui.color(3) | curses.A_BOLD
        if key == tab:
            attr |= curses.A_REVERSE
        ui.safe_addstr(win, 3, tab_x, label[: max(0, w - tab_x - 1)], attr)
        tab_x += len(label) + 1
        if tab_x >= w - 2:
            break
    if searching:
        ui.centered(win, h // 2, "Wondering... asking sources at once.",
                    ui.color(1) | curses.A_BOLD)
        ui.footer(win, "Searching (short timeout per source) - q cancels...")
        try:
            win.refresh()
        except curses.error:
            pass
        return
    msg_y = 4
    if errors and not results:
        ui.centered(win, msg_y, "No internet right now - showing what we can.",
                    ui.color(5) | curses.A_BOLD)
        msg_y += 1
        for src, err in sorted(errors.items()):
            if msg_y >= h - 2:
                break
            ui.centered(win, msg_y, ("%s: %s" % (src, err))[: w - 2],
                        ui.color(7))
            msg_y += 1
    elif errors:
        bits = ", ".join("%s %s" % (s, e) for s, e in sorted(errors.items()))
        ui.centered(win, msg_y, ("Some sources skipped (%s)" % bits)[: w - 2],
                    ui.color(7))
        msg_y += 1
    shown = filter_by_tab(results, tab)
    if not shown:
        if last_query:
            ui.centered(win, msg_y + 1,
                        "No results for '%s' on this tab. Try All!" % (
                            last_query[:30]),
                        ui.color(7) | curses.A_BOLD)
        else:
            ui.centered(win, msg_y + 1, "Type a question, hit Enter.",
                        ui.color(7) | curses.A_BOLD)
            ui.centered(win, msg_y + 3, "Left/Right picks a source tab first,",
                        ui.color(7))
            ui.centered(win, msg_y + 4, "or just search everything at once.",
                        ui.color(7))
            ui.centered(win, msg_y + 5, "Example: penguins, tetris, black holes",
                        ui.color(7))
    else:
        badge = " (cached)" if from_cache else ""
        ui.safe_addstr(win, msg_y, 2,
                       "%d result%s for '%s'%s (Enter reads)" % (
                           len(shown), "" if len(shown) == 1 else "s",
                           last_query[:30], badge),
                       ui.color(2) | curses.A_BOLD)
        per_page = results_per_page(win)
        for i in range(per_page):
            idx = top + i
            if idx >= len(shown):
                break
            r = shown[idx]
            y = msg_y + 1 + i * 5
            if y + 3 >= h - 1:
                break
            selected = idx == sel
            attr = curses.A_REVERSE | curses.A_BOLD if selected else curses.A_BOLD
            tag = "[%s]" % search_mod.SOURCE_LABELS.get(r["source"],
                                                        r["source"][:4].upper())
            title = "%s %s" % (tag, r["title"])
            ui.safe_addstr(win, y, 2,
                           ("> " if selected else "  ") + title[: w - 5],
                           attr | ui.color(SOURCE_COLORS.get(r["source"], 7)))
            for j, line in enumerate(wrap_snippet(r["snippet"], w - 8, 3)):
                if y + 1 + j >= h - 1:
                    break
                ui.safe_addstr(win, y + 1 + j, 4, line, ui.color(7))
            ui.safe_addstr(win, y + 4, 4, r["url"][: w - 7],
                           ui.color(SOURCE_COLORS.get(r["source"], 1)))
        pages = max(1, (len(shown) + per_page - 1) // per_page)
        page = min(pages, top // per_page + 1)
        if pages > 1:
            ui.safe_addstr(win, h - 2, max(0, w - 18),
                           "page %d/%d (Up/Down)" % (page, pages),
                           ui.color(3))
    ui.game_footer(win, "Type+Enter search | Up/Down pick | Left/Right tab | "
                        "Enter read | Esc menu")
    try:
        win.refresh()
    except curses.error:
        pass


def _detail_lines(result, w):
    """Wrap a search result into display lines for the detail panel."""
    words, lines, cur = (result.get("snippet") or "(no summary)").split(" "), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > max(20, w - 6):
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    lines.append("")
    lines.append("Link:")
    url = result.get("url") or ""
    if not isinstance(url, str):
        try:
            url = str(url)
        except Exception:
            url = ""
    while url:
        lines.append(url[: max(20, w - 6)])
        url = url[max(20, w - 6):]
    return lines


def _loading_screen(win, message):
    try:
        win.clear()
        h, w = win.getmaxyx()
        ui.centered(win, h // 2, message[: w - 2],
                    ui.color(3) | curses.A_BOLD)
        ui.footer(win, "Fetching the full text - q cancels...")
        win.refresh()
    except curses.error:
        pass


def _fetch_with_cancel(win, result):
    """fetch_full in a thread so q/Esc cancels the wait. Never raises."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(search_mod.fetch_full, result)
    _loading_screen(win, "Opening the full story...")
    try:
        win.timeout(150)
    except curses.error:
        pass
    dots = 0
    while not future.done():
        dots = (dots + 1) % 4
        _loading_screen(win, "Opening the full story" + "." * dots)
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            try:
                win.timeout(-1)
            except curses.error:
                pass
            return {"cancelled": True}
        if key == curses.KEY_RESIZE:
            continue
    try:
        win.timeout(-1)
    except curses.error:
        pass
    try:
        return future.result()
    except Exception as exc:
        return {"error": str(exc)[:80] or "fetch failed"}


def show_detail(win, result):
    try:
        win.timeout(-1)
    except curses.error:
        pass
    top = 0
    lines = []
    while True:
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, str(result.get("title", ""))[: max(0, w - 2)],
                      "[%s]" % str(result.get("source", "?")).upper())
            lines = _detail_lines(result, w)
            visible = max(1, h - 5)
            for i in range(visible):
                idx = top + i
                if idx >= len(lines):
                    break
                ui.safe_addstr(win, 3 + i, 3, lines[idx][: w - 6], ui.color(7))
            if top + visible < len(lines):
                ui.safe_addstr(win, h - 2, w - 12, "(more: Up/Down)", ui.color(3))
            ui.footer(win, "Up/Down scroll | any other key back to results")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key == curses.KEY_UP:
            top = max(0, top - 1)
        elif key == curses.KEY_DOWN:
            try:
                h, _ = win.getmaxyx()
            except curses.error:
                h = 24
            visible = max(1, h - 5)
            top = min(top + 1, max(0, len(lines) - visible))
        elif key == curses.KEY_RESIZE:
            continue
        elif key != -1:
            return


def show_reader(win, results, index):
    """Full-screen reader for full article text. 'n' opens the next one."""
    idx = index
    doc, lines = None, []
    top = 0
    find_term, find_hits, find_pos = "", [], 0
    status = ""
    while 0 <= idx < len(results):
        result = results[idx]
        doc = _fetch_with_cancel(win, result)
        if isinstance(doc, dict) and doc.get("cancelled"):
            return "cancelled"
        if isinstance(doc, dict) and doc.get("error"):
            body = "Could not load the full text (%s).\n\n%s\n\nLINK\n%s" % (
                doc["error"], result.get("snippet") or "",
                result.get("url") or "")
            doc = {"title": result.get("title") or "",
                   "source": result.get("source") or "",
                   "url": result.get("url") or "", "body": body}
        try:
            _, w = win.getmaxyx()
        except curses.error:
            w = 80
        lines = wrap_text(doc.get("body") or "(empty)", max(20, w - 6))
        top = 0
        find_term, find_hits, find_pos = "", [], 0
        status = ""
        while True:
            if ui.too_small(win, 12, 50):
                ui.show_too_small(win)
                try:
                    key = win.getch()
                except curses.error:
                    key = -1
                if key in ui.QUIT_KEYS:
                    return "back"
                continue
            try:
                win.clear()
                h, w = win.getmaxyx()
                head = str(doc.get("title") or "")[: max(0, w - 2)]
                sub = "[%s]  %d/%d  (n next, / find)" % (
                    str(doc.get("source") or "?").upper(), idx + 1,
                    len(results))
                ui.header(win, head, sub[: max(0, w - 2)])
                visible = max(1, h - 5)
                for i in range(visible):
                    line_idx = top + i
                    if line_idx >= len(lines):
                        break
                    attr = ui.color(7)
                    if (find_term and find_term.lower()
                            in lines[line_idx].lower()):
                        attr = ui.color(8) | curses.A_BOLD
                    ui.safe_addstr(win, 3 + i, 3, lines[line_idx][: w - 6],
                                   attr)
                footer_bits = "Up/Down/PgUp/PgDn/Home/End scroll"
                if idx + 1 < len(results):
                    footer_bits += " | n next"
                footer_bits += " | / find | q back"
                if top + visible < len(lines):
                    ui.safe_addstr(win, h - 2, max(0, w - 20),
                                   "(more: scroll down)", ui.color(3))
                if status:
                    ui.centered(win, h - 2, status[: w - 2],
                                ui.color(3) | curses.A_BOLD)
                ui.footer(win, footer_bits)
                win.refresh()
            except curses.error:
                pass
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return "back"
            if key == curses.KEY_RESIZE:
                try:
                    _, w = win.getmaxyx()
                except curses.error:
                    w = 80
                lines = wrap_text(doc.get("body") or "", max(20, w - 6))
                continue
            if key == curses.KEY_UP:
                top = max(0, top - 1)
            elif key == curses.KEY_DOWN:
                try:
                    h, _ = win.getmaxyx()
                except curses.error:
                    h = 24
                top = min(top + 1, max(0, len(lines) - max(1, h - 5)))
            elif key == curses.KEY_PPAGE:
                try:
                    h, _ = win.getmaxyx()
                except curses.error:
                    h = 24
                top = max(0, top - max(1, h - 5))
            elif key == curses.KEY_NPAGE:
                try:
                    h, _ = win.getmaxyx()
                except curses.error:
                    h = 24
                top = min(top + max(1, h - 5),
                          max(0, len(lines) - max(1, h - 5)))
            elif key == curses.KEY_HOME:
                top = 0
            elif key == curses.KEY_END:
                try:
                    h, _ = win.getmaxyx()
                except curses.error:
                    h = 24
                top = max(0, len(lines) - max(1, h - 5))
            elif key in (ord("n"), ord("N")):
                if idx + 1 < len(results):
                    idx += 1
                    break
                status = "That was the last result."
            elif key == ord("/"):
                term = _find_prompt(win, find_term)
                if term is None:
                    continue
                if term == "" and find_term:
                    term = find_term
                    start = find_pos + 1
                else:
                    start = 0
                find_term = term
                find_hits = ([i for i, ln in enumerate(lines)
                              if term.lower() in ln.lower()]
                             if term else [])
                if not find_hits:
                    status = ("No match for '%s'." % term[:30]) if term \
                        else "Find cleared."
                    continue
                pos = next((p for p in range(len(find_hits))
                            if find_hits[p] >= (top if start == 0
                                                else top + 1)),
                           0)
                find_pos = find_hits[pos]
                top = max(0, find_pos - 2)
                status = "Match %d of %d for '%s' (/ again: next)" % (
                    pos + 1, len(find_hits), term[:30])
            elif key in ui.HELP_KEYS:
                ui.show_help_overlay(win, TITLE, CONTROLS)
    return "back"


def _find_prompt(win, initial=""):
    buf = initial or ""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            _, w = win.getmaxyx()
            ui.footer(win, "Find: " + (buf + "_")[: max(0, w - 8)])
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key == 27:
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return buf.strip()
        if key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= key <= 126 and len(buf) < 40:
            buf += chr(key)


def _run_search(win, query, cache):
    """Search with an animated loading screen; q cancels the wait."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(search_mod.search_all_cached, query, 4, None, cache)
    frames = ["Wondering.", "Wondering..", "Wondering..."]
    frame = 0
    try:
        win.timeout(200)
    except curses.error:
        pass
    while not future.done():
        draw_screen(win, query, [], {}, 0, 0, False, query)
        try:
            h, w = win.getmaxyx()
            ui.centered(win, h // 2, frames[frame % len(frames)][: w - 2],
                        ui.color(1) | curses.A_BOLD)
            ui.footer(win, "Searching (short timeout per source) - q cancels")
            win.refresh()
        except curses.error:
            pass
        frame += 1
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            try:
                win.timeout(-1)
            except curses.error:
                pass
            return None, None, False, True
        if key == curses.KEY_RESIZE:
            continue
    try:
        win.timeout(-1)
    except curses.error:
        pass
    try:
        results, errors, from_cache = future.result()
    except Exception:
        return [], {"search": "unavailable - skipping"}, False, False
    return results, errors, from_cache, False


def play(stdscr, score_store):
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    query, results, errors = "", [], {}
    sel = top = 0
    last_query = ""
    from_cache = False
    tab = "all"
    hist = get_history(score_store)
    cache = load_query_cache()
    while True:
        if ui.too_small(stdscr):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        shown = filter_by_tab(results, tab)
        if shown:
            sel = max(0, min(sel, len(shown) - 1))
            per_page = results_per_page(stdscr)
            if sel < top:
                top = sel
            elif sel >= top + per_page:
                top = sel - per_page + 1
        else:
            sel = top = 0
        if not query and not results and not last_query and hist:
            draw_screen(stdscr, query, results, errors, sel, top, False,
                        last_query, tab)
            try:
                h, w = stdscr.getmaxyx()
                hint = "History (Up recalls): " + ", ".join(hist[:3])
                ui.safe_addstr(stdscr, 3, 2, hint[: w - 4], ui.color(7))
                stdscr.refresh()
            except curses.error:
                pass
        else:
            draw_screen(stdscr, query, results, errors, sel, top, False,
                        last_query, tab, from_cache)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            try:
                save_query_cache(cache)
            except Exception:
                pass
            return
        if key == curses.KEY_RESIZE:
            continue
        if key == ord("?"):
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        shown = filter_by_tab(results, tab)
        if key == curses.KEY_UP:
            if shown:
                sel = (sel - 1) % len(shown)
            elif hist and not query:
                query = hist[0]
            elif hist:
                try:
                    i = hist.index(query)
                    query = hist[(i + 1) % len(hist)]
                except ValueError:
                    query = hist[0]
            continue
        if key == curses.KEY_DOWN:
            if shown:
                sel = (sel + 1) % len(shown)
            elif hist:
                try:
                    i = hist.index(query)
                    query = hist[(i - 1) % len(hist)]
                except ValueError:
                    query = hist[-1] if hist else query
            continue
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            step = 1 if key == curses.KEY_RIGHT else -1
            tab = TABS[(TABS.index(tab) + step) % len(TABS)]
            sel = top = 0
            continue
        if key in (10, 13, curses.KEY_ENTER):
            if shown and query.strip() == last_query and last_query:
                show_reader(stdscr, shown, sel)
                continue
            if not query.strip():
                if shown:
                    show_reader(stdscr, shown, sel)
                continue
            last_query = query.strip()
            results, errors, from_cache, cancelled = _run_search(
                stdscr, last_query, cache)
            if cancelled:
                continue
            if results is None:
                continue
            try:
                save_query_cache(cache)
            except Exception:
                pass
            sel, top = 0, 0
            add_history(score_store, last_query)
            hist = get_history(score_store)
            continue
        if key in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
            from_cache = False
            continue
        if 32 <= key <= 126:
            if len(query) < 80:
                query += chr(key)
                from_cache = False
            continue

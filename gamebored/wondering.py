"""Bored Wondering UI: type a query, browse merged results, read details."""

import curses

from . import scores as scores_mod
from . import search as search_mod
from . import ui

TITLE = "Bored Wondering"
DESCRIPTION = "Search the web, keyless"
CONTROLS = "Type + Enter search | Up/Down pick | Enter open | q/Esc menu"
GAME_ID = "wondering"
CATEGORY = "Explore"

SOURCE_COLORS = {"wikipedia": 1, "duckduckgo": 4, "hackernews": 3}

HISTORY_KEY = "_wonder_history"


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


def _visible_rows(win):
    try:
        h, _ = win.getmaxyx()
        return max(1, (h - 8) // 3)
    except curses.error:
        return 4


def draw_screen(win, query, results, errors, sel, top, searching,
                last_query):
    try:
        win.clear()
    except curses.error:
        pass
    h, w = win.getmaxyx()
    ui.header(win, "BORED WONDERING", "the keyless corner of the internet")
    ui.safe_addstr(win, 2, 2, "Ask: " + (query + "_")[: max(0, w - 8)],
                   curses.A_BOLD | ui.color(3))
    if searching:
        ui.centered(win, h // 2, "Wondering... asking 3 sources at once.",
                    ui.color(1) | curses.A_BOLD)
        ui.footer(win, "Searching (short timeout per source)...")
        try:
            win.refresh()
        except curses.error:
            pass
        return
    msg_y = 3
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
    if not results:
        if last_query:
            ui.centered(win, msg_y + 1,
                        "No results for '%s'. Try another word!" % last_query[:30],
                        ui.color(7) | curses.A_BOLD)
        else:
            ui.centered(win, msg_y + 1, "Type a question, hit Enter.",
                        ui.color(7) | curses.A_BOLD)
        ui.centered(win, msg_y + 2, "Example: penguins, tetris, black holes",
                    ui.color(7))
    else:
        ui.safe_addstr(win, msg_y, 2,
                       "%d results for '%s' (Enter opens)" % (
                           len(results), last_query[:30]),
                       ui.color(2) | curses.A_BOLD)
        per_row = 3
        rows_visible = max(1, (h - msg_y - 3) // per_row)
        for i in range(rows_visible):
            idx = top + i
            if idx >= len(results):
                break
            r = results[idx]
            y = msg_y + 1 + i * per_row
            if y + 2 >= h - 1:
                break
            selected = idx == sel
            attr = curses.A_REVERSE | curses.A_BOLD if selected else curses.A_BOLD
            tag = "[%s]" % (r["source"][:4].upper())
            line = "%s %s" % (tag, r["title"])
            ui.safe_addstr(win, y, 2,
                           ("> " if selected else "  ") + line[: w - 5],
                           attr | ui.color(SOURCE_COLORS.get(r["source"], 7)))
            ui.safe_addstr(win, y + 1, 4, r["snippet"][: w - 7], ui.color(7))
            ui.safe_addstr(win, y + 2, 4, r["url"][: w - 7],
                           ui.color(SOURCE_COLORS.get(r["source"], 1)))
    ui.game_footer(win, "Type + Enter search | Up/Down pick | Enter open | Esc menu")
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
    hist = get_history(score_store)
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
        if not query and not results and not last_query and hist:
            # show a history hint under the prompt
            draw_screen(stdscr, query, results, errors, sel, top, False,
                        last_query)
            try:
                h, w = stdscr.getmaxyx()
                hint = "History (Up recalls): " + ", ".join(hist[:3])
                ui.safe_addstr(stdscr, 3, 2, hint[: w - 4], ui.color(7))
                stdscr.refresh()
            except curses.error:
                pass
        else:
            draw_screen(stdscr, query, results, errors, sel, top, False,
                        last_query)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        if key == curses.KEY_RESIZE:
            continue
        if key == ord("?"):
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key == curses.KEY_UP:
            if results:
                sel = (sel - 1) % len(results)
                if sel < top:
                    top = sel
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
            if results:
                sel = (sel + 1) % len(results)
                if sel >= top + _visible_rows(stdscr):
                    top = sel - _visible_rows(stdscr) + 1
            elif hist:
                try:
                    i = hist.index(query)
                    query = hist[(i - 1) % len(hist)]
                except ValueError:
                    query = hist[-1] if hist else query
            continue
        if key in (10, 13, curses.KEY_ENTER):
            # If results are on screen and the query is unchanged since the
            # search, Enter opens the highlighted result. Otherwise search.
            if results and query.strip() == last_query and last_query:
                show_detail(stdscr, results[sel])
                continue
            if not query.strip():
                if results:  # empty prompt + Enter opens highlighted result
                    show_detail(stdscr, results[sel])
                continue
            last_query = query.strip()
            draw_screen(stdscr, query, results, errors, sel, top, True,
                        last_query)
            res, errs = search_mod.search_all(last_query, timeout=4)
            results, errors = res, errs
            sel, top = 0, 0
            add_history(score_store, last_query)
            hist = get_history(score_store)
            if not results and not errors:
                pass
            continue
        if key == curses.KEY_RIGHT and results:
            show_detail(stdscr, results[sel])
            continue
        if key in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
            continue
        if 32 <= key <= 126:
            if len(query) < 80:
                query += chr(key)
            continue

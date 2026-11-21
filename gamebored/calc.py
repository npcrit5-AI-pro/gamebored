"""Calculator app: safe arithmetic with no eval().

Expressions are parsed with ast and only plain numbers plus + - * / //
% ** and parentheses are allowed. Anything else (names, calls, attribute
access, dunders) is rejected. History persists in the data dir.
"""

import ast
import curses
import operator

from . import storage as storage_mod
from . import ui

TITLE = "Calculator"
DESCRIPTION = "Quick safe arithmetic"
CONTROLS = "Type expression | Enter evaluate | Up history | q menu"
GAME_ID = "calc"
CATEGORY = "Tools"

HISTORY_NAME = "calc.json"
HISTORY_LIMIT = 20

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CalcError(ValueError):
    pass


def _eval_node(node, depth=0):
    if depth > 64:
        raise CalcError("too deeply nested")
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, depth + 1)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise CalcError("only numbers allowed")
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalcError("only numbers allowed")
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise CalcError("operator not allowed")
        left = _eval_node(node.left, depth + 1)
        right = _eval_node(node.right, depth + 1)
        if isinstance(right, int) and abs(right) > 10**6:
            raise CalcError("number too big")
        try:
            result = op(left, right)
        except ZeroDivisionError:
            raise CalcError("division by zero")
        except (OverflowError, ValueError, ArithmeticError):
            raise CalcError("result out of range")
        if isinstance(result, complex):
            raise CalcError("real numbers only")
        if isinstance(result, bool):
            raise CalcError("only numbers allowed")
        if isinstance(result, float) and (
                result != result or result in (float("inf"),
                                               float("-inf"))):
            raise CalcError("result out of range")
        if isinstance(result, int) and abs(result) >= 10**18:
            raise CalcError("result out of range")
        return result
    if isinstance(node, ast.UnaryOp):
        op = _UNARYOPS.get(type(node.op))
        if op is None:
            raise CalcError("operator not allowed")
        return op(_eval_node(node.operand, depth + 1))
    raise CalcError("only numbers allowed")


def evaluate(expression):
    """Evaluate an arithmetic expression. Raises CalcError when invalid."""
    if not isinstance(expression, str):
        raise CalcError("type an expression")
    text = expression.strip().replace("^", "**").replace("×", "*").replace(
        "÷", "/")
    if not text:
        raise CalcError("type an expression")
    if len(text) > 120:
        raise CalcError("expression too long")
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, MemoryError):
        raise CalcError("not a valid expression")
    if not isinstance(tree, ast.Expression):
        raise CalcError("not a valid expression")
    value = _eval_node(tree)
    if isinstance(value, bool):
        raise CalcError("only numbers allowed")
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CalcError("result out of range")
        if value.is_integer() and abs(value) < 10**15:
            return int(value)
        return round(value, 10)
    if isinstance(value, int) and abs(value) >= 10**18:
        raise CalcError("result out of range")
    return value


def format_value(value):
    if isinstance(value, int):
        return "%d" % value
    if isinstance(value, float):
        text = "%.10f" % value
        return text.rstrip("0").rstrip(".") or "0"
    return str(value)


def load_history(path=None):
    raw = storage_mod.load_json(HISTORY_NAME, [],
                                path=path or storage_mod.data_path(HISTORY_NAME))
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and "expr" in item and "result" in item:
            out.append({"expr": str(item["expr"])[:120],
                        "result": str(item["result"])[:60]})
    return out[-HISTORY_LIMIT:]


def add_history(history, expr, result, path=None):
    history = list(history or [])
    history.append({"expr": expr, "result": result})
    history = history[-HISTORY_LIMIT:]
    try:
        storage_mod.save_json(HISTORY_NAME, history,
                              path=path or storage_mod.data_path(HISTORY_NAME))
    except Exception:
        pass
    return history


def play(stdscr, _score_store=None):
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    buf = ""
    history = load_history()
    hist_pos = None
    message = ""
    while True:
        if ui.too_small(stdscr, 12, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.header(stdscr, "CALCULATOR", "safe arithmetic, no surprises")
            ui.safe_addstr(stdscr, 3, 2, "> " + (buf + "_")[: max(0, w - 6)],
                           curses.A_BOLD | ui.color(3))
            if message:
                ui.centered(stdscr, 5, message[: w - 2],
                            ui.color(2) | curses.A_BOLD)
            row = 7
            shown = history[-max(0, h - row - 2):]
            for item in reversed(shown):
                line = "%s = %s" % (item["expr"], item["result"])
                ui.safe_addstr(stdscr, row, 4, line[: w - 8], ui.color(7))
                row += 1
                if row >= h - 1:
                    break
            ui.game_footer(stdscr, CONTROLS)
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        if key == curses.KEY_RESIZE:
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key in (10, 13, curses.KEY_ENTER):
            if not buf.strip():
                continue
            try:
                value = evaluate(buf)
                answer = format_value(value)
                message = "%s = %s" % (buf.strip(), answer)
                history = add_history(history, buf.strip(), answer)
                hist_pos = None
            except CalcError as exc:
                message = "Nope: %s" % exc
            buf = ""
            continue
        if key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
            hist_pos = None
            continue
        if key == curses.KEY_UP and history:
            if hist_pos is None:
                hist_pos = len(history) - 1
            else:
                hist_pos = max(0, hist_pos - 1)
            buf = history[hist_pos]["expr"]
            continue
        if key == curses.KEY_DOWN and history and hist_pos is not None:
            hist_pos = hist_pos + 1
            if hist_pos >= len(history):
                hist_pos = None
                buf = ""
            else:
                buf = history[hist_pos]["expr"]
            continue
        if 32 <= key <= 126 and len(buf) < 120:
            buf += chr(key)
            hist_pos = None

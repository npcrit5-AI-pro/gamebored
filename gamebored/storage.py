"""Atomic JSON storage shared by GameBored apps (notes, todos, settings).

Every write goes to a temp file plus rename so a crash mid-save can never
leave half a file behind. Only the standard library is used.
"""

import json
import os

from . import scores as scores_mod


def app_dir():
    return scores_mod.APP_DIR


def data_path(name):
    return os.path.join(app_dir(), name)


def load_json(name, default, path=None):
    """Load a JSON document; return default on any error or wrong shape."""
    full = path or data_path(name)
    try:
        with open(full, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data
    except (OSError, ValueError):
        pass
    return default


def save_json(name, data, path=None):
    """Atomically save a JSON document. Never raises."""
    full = path or data_path(name)
    try:
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except OSError:
        return
    tmp_path = full + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        os.replace(tmp_path, full)
    except (OSError, TypeError, ValueError):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def data_size_bytes():
    """Total bytes used under the data dir (0 when unknown)."""
    total = 0
    root = app_dir()
    try:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".tmp"):
                    continue
                try:
                    total += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass
    except OSError:
        pass
    return total

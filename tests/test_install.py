"""Installer round-trip test: install.sh/uninstall.sh with a scratch HOME.

Uses only the stdlib (subprocess + bash, both guaranteed on the Fedora
console this project targets). Never touches the real HOME.
"""

import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(REPO, "install.sh")
UNINSTALL = os.path.join(REPO, "uninstall.sh")


def _run(script, home):
    env = dict(os.environ, HOME=home,
               PATH="/usr/bin:/bin:" + os.environ.get("PATH", ""))
    return subprocess.run(["bash", script], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=120)


def test_install_uninstall_roundtrip(tmp_path):
    if os.name != "posix":
        pytest.skip("installer targets POSIX shells")
    home = str(tmp_path / "home")
    os.makedirs(home)
    installed = _run(INSTALL, home)
    assert installed.returncode == 0, installed.stderr
    launcher = os.path.join(home, ".local", "bin", "GameBored")
    assert os.path.isfile(launcher) and os.access(launcher, os.X_OK)
    pkg = os.path.join(home, ".local", "share", "gamebored", "gamebored")
    assert os.path.isdir(pkg)
    env = dict(os.environ, HOME=home,
               PYTHONPATH=os.path.join(home, ".local", "share", "gamebored"))
    out = subprocess.run([sys.executable, "-m", "gamebored", "--version"],
                         env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "GameBored" in out.stdout
    removed = _run(UNINSTALL, home)
    assert removed.returncode == 0, removed.stderr
    assert not os.path.exists(launcher)
    assert not os.path.exists(
        os.path.join(home, ".local", "share", "gamebored"))


def test_scores_survive_uninstall_reinstall(tmp_path):
    if os.name != "posix":
        pytest.skip("installer targets POSIX shells")
    home = str(tmp_path / "home2")
    os.makedirs(home)
    assert _run(INSTALL, home).returncode == 0
    dest = os.path.join(home, ".local", "share", "gamebored")
    with open(os.path.join(dest, "scores.json"), "w") as fh:
        fh.write('{"snake": {"high": 9, "plays": 2, "wins": 0}}')
    assert _run(UNINSTALL, home).returncode == 0
    assert not os.path.exists(dest)
    backup = os.path.join(home, ".local", "share",
                          "gamebored-scores-backup.json")
    assert os.path.isfile(backup)
    assert _run(INSTALL, home).returncode == 0
    with open(os.path.join(dest, "scores.json")) as fh:
        assert '"high": 9' in fh.read()

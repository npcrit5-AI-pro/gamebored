#!/usr/bin/env bash
# GameBored uninstaller: removes the home install + launchers, keeps nothing.
set -euo pipefail

DEST="$HOME/.local/share/gamebored"
BIN_DIR="$HOME/.local/bin"

rm -f "$BIN_DIR/GameBored" "$BIN_DIR/gamebored"
rm -rf "$DEST"

echo "GameBored uninstalled."
echo "(Your shell rc may still export ~/.local/bin on PATH; harmless to keep.)"

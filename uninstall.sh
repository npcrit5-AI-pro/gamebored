#!/usr/bin/env bash
# GameBored uninstaller: removes the home install + launchers.
# Your high scores are backed up first, and the next install restores them.
set -euo pipefail

DEST="$HOME/.local/share/gamebored"
BACKUP="$HOME/.local/share/gamebored-scores-backup.json"
PROGRESS_BACKUP="$HOME/.local/share/gamebored-progress-backup.json"
BIN_DIR="$HOME/.local/bin"

if [[ -f "$DEST/scores.json" ]]; then
  cp "$DEST/scores.json" "$BACKUP"
  echo "High scores backed up to $BACKUP"
fi
if [[ -f "$DEST/progress.json" ]]; then
  cp "$DEST/progress.json" "$PROGRESS_BACKUP"
  echo "Room progress backed up to $PROGRESS_BACKUP"
fi

rm -f "$BIN_DIR/GameBored" "$BIN_DIR/gamebored"
rm -rf "$DEST"

echo "GameBored uninstalled."
echo "(Your shell rc may still export ~/.local/bin on PATH; harmless to keep.)"

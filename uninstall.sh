#!/usr/bin/env bash
# GameBored uninstaller: removes the home install + launchers.
# Your data (scores, progress, notes, to-dos, settings, Eliza memory,
# Animals tree) is backed up first, and the next install restores it.
set -euo pipefail

DEST="$HOME/.local/share/gamebored"
BACKUP="$HOME/.local/share/gamebored-scores-backup.json"
PROGRESS_BACKUP="$HOME/.local/share/gamebored-progress-backup.json"
BIN_DIR="$HOME/.local/bin"

backup_file() {
  # backup_file <dest-name> <backup-name>: stash user data before wiping.
  if [[ -f "$DEST/$1" ]]; then
    cp "$DEST/$1" "$HOME/.local/share/$2"
    echo "$1 backed up to $HOME/.local/share/$2"
  fi
}
if [[ -f "$DEST/scores.json" ]]; then
  cp "$DEST/scores.json" "$BACKUP"
  echo "High scores backed up to $BACKUP"
fi
if [[ -f "$DEST/progress.json" ]]; then
  cp "$DEST/progress.json" "$PROGRESS_BACKUP"
  echo "Room progress backed up to $PROGRESS_BACKUP"
fi
backup_file "todos.json" "gamebored-todos-backup.json"
backup_file "settings.json" "gamebored-settings-backup.json"
backup_file "calc.json" "gamebored-calc-backup.json"
backup_file "wonder_cache.json" "gamebored-wonder-cache-backup.json"
backup_file "eliza_memory.json" "gamebored-eliza-memory-backup.json"
backup_file "animals_tree.json" "gamebored-animals-tree-backup.json"
if [[ -d "$DEST/notes" ]]; then
  rm -rf "$HOME/.local/share/gamebored-notes-backup"
  cp -r "$DEST/notes" "$HOME/.local/share/gamebored-notes-backup"
  echo "Notes backed up to $HOME/.local/share/gamebored-notes-backup"
fi

rm -f "$BIN_DIR/GameBored" "$BIN_DIR/gamebored"
rm -rf "$DEST"

echo "GameBored uninstalled."
echo "(Your shell rc may still export ~/.local/bin on PATH; harmless to keep.)"

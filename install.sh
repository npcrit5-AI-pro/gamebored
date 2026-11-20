#!/usr/bin/env bash
# GameBored installer: no sudo, installs into the user's home.
# Usage: ./install.sh
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/gamebored"
BIN_DIR="$HOME/.local/bin"

echo "Installing GameBored..."

mkdir -p "$DEST" "$BIN_DIR"

# Copy the game package (and nothing else) to ~/.local/share/gamebored
rm -rf "$DEST/gamebored"
cp -r "$SRC_DIR/gamebored" "$DEST/gamebored"
# Drop caches if the repo shipped any
find "$DEST" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

# Launcher: case-insensitive friendly (GameBored + gamebored)
cat > "$BIN_DIR/GameBored" <<'EOF'
#!/usr/bin/env bash
# GameBored launcher: runs the home install with stock python3, no pip needed.
export PYTHONPATH="$HOME/.local/share/gamebored:${PYTHONPATH:-}"
exec python3 -m gamebored "$@"
EOF
chmod +x "$BIN_DIR/GameBored"
ln -sf "GameBored" "$BIN_DIR/gamebored"

# Make sure ~/.local/bin is on PATH (it is by default on Fedora 43+,
# but harmless to ensure for custom shells).
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$RC" ]]; then
      if ! grep -q '\.local/bin' "$RC" 2>/dev/null; then
        # shellcheck disable=SC2016
        printf '\n# GameBored: put user binaries on PATH\n' >> "$RC"
        printf 'export PATH="$HOME/.local/bin:$PATH"\n' >> "$RC"
        echo "Added ~/.local/bin to PATH in $RC"
      fi
    fi
  done
  export PATH="$HOME/.local/bin:$PATH"
fi

echo ""
echo "Done! Launch with:"
echo "    GameBored      (or: gamebored)"
echo ""
echo "Scores live in ~/.local/share/gamebored/scores.json"
echo "If 'GameBored' is not found, restart your shell or run:"
echo '    export PATH="$HOME/.local/bin:$PATH"'

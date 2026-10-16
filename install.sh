#!/usr/bin/env bash
# Install flag-colorscript into ~/.local (override with PREFIX=/some/dir).
#   ./install.sh            install / update
#   ./install.sh uninstall  remove
set -e

PREFIX="${PREFIX:-$HOME/.local}"
SHARE="$PREFIX/share/flag-colorscript"
BIN="$PREFIX/bin"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "uninstall" ]; then
    rm -rf "$SHARE"
    rm -f "$BIN/flag-colorscript"
    echo "flag-colorscript uninstalled."
    exit 0
fi

rm -rf "$SHARE"
mkdir -p "$SHARE" "$BIN"
cp -R "$HERE/colorscripts" "$HERE/names.tsv" "$HERE/flag-colorscript" "$SHARE/"
chmod +x "$SHARE/flag-colorscript"
ln -sf "$SHARE/flag-colorscript" "$BIN/flag-colorscript"

echo "Installed to $SHARE"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "Note: $BIN is not on your PATH. Add this to ~/.zshrc:"
       echo "  export PATH=\"$BIN:\$PATH\"" ;;
esac
echo "To show a flag in every new shell, add this to the end of ~/.zshrc:"
echo "  flag-colorscript"

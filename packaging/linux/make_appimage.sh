#!/usr/bin/env bash
# Assemble an AppImage from the package produced by PyInstaller.
# An AppImage is a single file, runnable on most distributions without
# installing anything.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$ROOT/dist/Maelstrom"
APPDIR="$ROOT/build/AppDir"
VERSION="${1:-dev}"
ARCH="${ARCH:-x86_64}"

[ -d "$DIST" ] || { echo "Package not found: $DIST" >&2; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -a "$DIST/." "$APPDIR/usr/bin/"
cp "$ROOT/packaging/linux/maelstrom.desktop" \
   "$APPDIR/usr/share/applications/maelstrom.desktop"
cp "$ROOT/packaging/linux/maelstrom.desktop" "$APPDIR/maelstrom.desktop"
cp "$ROOT/packaging/icon.png" \
   "$APPDIR/usr/share/icons/hicolor/256x256/apps/maelstrom.png"
cp "$ROOT/packaging/icon.png" "$APPDIR/maelstrom.png"

cat > "$APPDIR/AppRun" <<'LAUNCHER'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Maelstrom" "$@"
LAUNCHER
chmod +x "$APPDIR/AppRun"

TOOL="$ROOT/build/appimagetool"
if [ ! -x "$TOOL" ]; then
  echo "Downloading appimagetool..."
  mkdir -p "$(dirname "$TOOL")"
  curl -sSL -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  chmod +x "$TOOL"
fi

OUTPUT="$ROOT/dist/Maelstrom-${VERSION}-${ARCH}.AppImage"
# --appimage-extract-and-run: no need for FUSE, which continuous integration
# containers usually do not have.
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT"
echo "AppImage: $OUTPUT"

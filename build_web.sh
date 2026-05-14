#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build_web.sh — Build Knights of Eldoria as a browser/PWA (WebAssembly)
#
# Requirements:
#   pip install pygbag pillow
#
# Usage:
#   ./build_web.sh          # build to build/web/
#   ./build_web.sh --serve  # build and open a local preview server
# ─────────────────────────────────────────────────────────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════╗"
echo "║  Knights of Eldoria — Web Build      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Generate icons if missing ─────────────────────────────────────────────
if [ ! -f web/icon-192.png ] || [ ! -f web/icon-512.png ]; then
  echo "→ Generating PWA icons…"
  python3 make_icons.py
else
  echo "→ Icons present ✓"
fi

# ── 2. Run Pygbag build ───────────────────────────────────────────────────────
echo ""
echo "→ Running pygbag build (this may take 2-5 minutes on first run)…"
echo ""

python3 -m pygbag \
  --build \
  --app_name "Knights of Eldoria" \
  --icon web/icon-512.png \
  --title "Knights of Eldoria" \
  .

# Pygbag outputs to build/web/ by default
BUILD_DIR="$ROOT/build/web"

# ── 3. Copy PWA files into the build directory ────────────────────────────────
echo ""
echo "→ Copying PWA files into build output…"

cp web/manifest.json   "$BUILD_DIR/manifest.json"
cp web/sw.js           "$BUILD_DIR/sw.js"
cp web/icon-192.png    "$BUILD_DIR/icon-192.png"
cp web/icon-512.png    "$BUILD_DIR/icon-512.png"
cp web/index.html      "$BUILD_DIR/index.html"

# ── 4. Patch the build's index.html to add PWA meta tags ─────────────────────
# Pygbag generates its own index.html — inject manifest link into <head>
PYGBAG_INDEX="$BUILD_DIR/index.html"
if grep -q "PYGBAG_SCRIPT_PLACEHOLDER" "$PYGBAG_INDEX" 2>/dev/null; then
  echo "→ Using our custom index.html (already has placeholder) ✓"
else
  # Pygbag overwrote it — inject manifest link
  sed -i.bak 's|</head>|  <link rel="manifest" href="manifest.json" />\n  <link rel="apple-touch-icon" href="icon-192.png" />\n  <meta name="apple-mobile-web-app-capable" content="yes" />\n  <meta name="theme-color" content="#12091e" />\n</head>|' "$PYGBAG_INDEX"
  echo "→ Injected PWA meta tags into pygbag index.html ✓"
fi

echo ""
echo "══════════════════════════════════════════"
echo "  Build complete!  →  $BUILD_DIR"
echo ""
echo "  Deploy options:"
echo "  • GitHub Pages : push the build/web/ contents to the gh-pages branch"
echo "  • itch.io      : zip build/web/ and upload as HTML game"
echo "  • Local test   : cd build/web && python3 -m http.server 8080"
echo "══════════════════════════════════════════"

# ── 5. Optional local preview ─────────────────────────────────────────────────
if [[ "$1" == "--serve" ]]; then
  echo ""
  echo "→ Starting local preview at http://localhost:8080 …"
  echo "   (Ctrl+C to stop)"
  cd "$BUILD_DIR" && python3 -m http.server 8080
fi

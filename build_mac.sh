#!/bin/bash
# Build PokelikeDebugger.app for macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use the project venv if present, otherwise expect deps to be installed globally
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "→ Installing / updating dependencies..."
pip install -r requirements.txt -q

echo "→ Cleaning previous build..."
rm -rf build dist

echo "→ Running PyInstaller..."
pyinstaller PokelikeDebugger.spec

echo ""
echo "✓ Done — dist/PokelikeDebugger.app"
echo "  Double-click to launch, or:"
echo "  open dist/PokelikeDebugger.app"

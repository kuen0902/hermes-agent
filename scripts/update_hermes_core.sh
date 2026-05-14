#!/bin/bash
# Hermes Agent Custom Update Script (Python 3.14 / venv_314 Compatible)
set -e

HERMES_DIR="$HOME/workspace/hermes-agent"
VENV_DIR="$HERMES_DIR/venv_314"
PYTHON_BIN="$VENV_DIR/bin/python"

echo "======================================"
echo "🔄 Updating Hermes Agent Core"
echo "======================================"

cd "$HERMES_DIR"

# 1. Pull latest code from upstream
echo "1. Pulling latest code..."
git pull

# 2. Re-install/sync dependencies into our custom venv_314
echo "2. Syncing dependencies to venv_314..."
if command -v uv &> /dev/null; then
    uv pip install -e ".[all]" --python "$PYTHON_BIN"
else
    "$PYTHON_BIN" -m pip install -e ".[all]"
fi

# 3. Ensure the global 'hermes' CLI points to the 3.14 environment
echo "3. Re-linking 'hermes' command..."
mkdir -p "$HOME/.local/bin"
ln -sf "$VENV_DIR/bin/hermes" "$HOME/.local/bin/hermes"

echo "======================================"
echo "✅ Update complete! Hermes is running on Python 3.14.4"
echo "======================================"

#!/bin/bash
set -e

echo "=== Upgrading Hermes Virtual Environment to Python 3.14.4 ==="

VENV_DIR="$HOME/.hermes/.venv"
PYTHON_CMD="/opt/homebrew/bin/python3"

# Verify global Python 3.14 is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "Error: Python 3.14 not found at $PYTHON_CMD"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
echo "Found $PYTHON_VERSION"

# Recreate venv
echo "Creating new virtual environment..."
$PYTHON_CMD -m venv "$VENV_DIR"

# Activate and install requirements
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"

pip install --upgrade pip

# Install required core dependencies based on previous environment state
pip install pandas requests urllib3 yfinance beautifulsoup4 peewee websockets rich curl_cffi scipy joblib xgboost pandas_ta_classic

echo "=== Upgrade Complete ==="
echo "The Hermes environment ($VENV_DIR) has been upgraded to Python 3.14.4."

#!/bin/zsh
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "First run: installing the small Python helper environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

python launcher.py

echo
echo "Bot stopped. Press Enter to close."
read

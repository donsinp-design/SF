#!/bin/zsh
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || {
  echo "Run UniversalDudley.command once first."
  read; exit 1
}
python test_keys.py
echo "Press Enter to close."
read

#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"
PYTHONUNBUFFERED=1 ./venv/bin/python bridge/watcher.py "$@"
read -p "Press Enter to close..."

#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ -f "./venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
else
    PYTHON=$(python3 -c "import json,sys; print(json.load(open('Engine/config.json'))['freecad_python'])" 2>/dev/null)
    if [ -z "$PYTHON" ] || [ ! -f "$PYTHON" ]; then
        PYTHON="/home/uli/squashfs-root/usr/bin/python"
    fi
fi

PYTHONUNBUFFERED=1 "$PYTHON" Engine/watcher.py "$@"
read -p "Press Enter to close..."

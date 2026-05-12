#!/bin/bash
set -e

echo "=========================================="
echo "  Fix paths after disk rename"
echo "=========================================="
echo ""

BRIDGE_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Update watcher.py shebang
WATCHER="$BRIDGE_DIR/watcher.py"
if [ -f "$WATCHER" ]; then
    echo "Updating watcher.py shebang..."
    sed -i 's|#!/mnt/Disc 470/Platicity_tp_FreeCAD/venv/bin/python|#!/mnt/Disc470/Platicity_tp_FreeCAD/venv/bin/python|' "$WATCHER"
    echo "  Done."
fi

# 2. Update venv paths
VENV="$BRIDGE_DIR/venv"
if [ -d "$VENV" ]; then
    echo "Updating venv paths..."
    OLD_PATH="/mnt/Disc 470/Platicity_tp_FreeCAD/venv"
    NEW_PATH="/mnt/Disc470/Platicity_tp_FreeCAD/venv"

    # Update activate script
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/bin/activate"
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/bin/activate.csh"
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/bin/activate.fish"

    # Update pip scripts
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/bin/pip" "$VENV/bin/pip3" "$VENV/bin/pip3.14" 2>/dev/null || true

    # Update watchmedo
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/bin/watchmedo" 2>/dev/null || true

    # Update pyvenv.cfg
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$VENV/pyvenv.cfg"

    echo "  Done."
fi

echo ""
echo "Verifying paths..."
echo "  watcher.py shebang: $(head -1 "$WATCHER")"
echo "  venv path: $(grep VIRTUAL_ENV "$VENV/bin/activate" | head -1 | cut -d"'" -f2)"

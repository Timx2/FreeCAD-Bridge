#!/bin/bash
set -e

ENGINE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$ENGINE_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
CONFIG_PATH="$PROJECT_DIR/Engine/config.json"
FREECAD_APPIMAGE="/home/uli/squashfs-root/AppRun"
FREECAD_MACRO_DIR="$HOME/.local/share/FreeCAD/v1-1/Macro"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            Plasticity → FreeCAD Bridge Setup                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  IMPORTANT: After setup, you must run this macro in FreeCAD │"
echo "│  once per session:                                          │"
echo "│                                                              │"
echo "│    Macro → Macros... → select 'reload_assembly' → Run       │"
echo "│                                                              │"
echo "│  This enables automatic assembly reload when parts change.  │"
echo "└──────────────────────────────────────────────────────────────┘"
echo ""

# 1. List available storage disks
echo "Available storage locations:"
echo "------------------------------------------"

DISK_NAMES=()
MOUNT_POINTS=()
IDX=1

while IFS= read -r line; do
    mount_pt=$(echo "$line" | awk '{print $NF}')
    mount_pt=$(echo -e "$mount_pt")

    if [[ "$mount_pt" == "/" || "$mount_pt" == "/boot" || "$mount_pt" == "/tmp" || "$mount_pt" == "/run" || "$mount_pt" == "none" || "$mount_pt" == "[SWAP]" || "$mount_pt" == "/var/log" ]]; then
        continue
    fi

    if [[ -z "$mount_pt" || "$mount_pt" == *"/snap/"* ]]; then
        continue
    fi

    disk_name=$(echo "$line" | awk '{print $1}')
    size=$(echo "$line" | awk '{print $3}')

    echo "  [$IDX] $disk_name ($size) → $mount_pt"
    DISK_NAMES+=("$disk_name")
    MOUNT_POINTS+=("$mount_pt")
    IDX=$((IDX + 1))
done < <(lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT --noheadings -r 2>/dev/null | grep -v '^[a-z0-9]* swap' | grep ' /')

if [ ${#MOUNT_POINTS[@]} -eq 0 ]; then
    echo "  No additional disks found. Using home directory."
    MOUNT_POINTS=("$HOME")
    echo "  [1] Home → $HOME"
    IDX=2
fi

echo "------------------------------------------"
echo ""

# 2. Ask user to select disk
read -rp "Select disk number [1-$((IDX - 1))]: " DISK_NUM

if [ -z "$DISK_NUM" ]; then
    DISK_NUM=1
fi

if [ "$DISK_NUM" -lt 1 ] || [ "$DISK_NUM" -ge "$IDX" ]; then
    echo "Error: Invalid selection."
    exit 1
fi

SELECTED_MOUNT="${MOUNT_POINTS[$((DISK_NUM - 1))]}"

echo ""

# 3. Ask for project name
read -rp "Project name (e.g. NozzleBracket): " PROJECT_NAME
if [ -z "$PROJECT_NAME" ]; then
    echo "Error: Project name cannot be empty."
    exit 1
fi

PROJECT_PATH="$SELECTED_MOUNT/$PROJECT_NAME"

# Ask if they want a custom subdirectory
read -rp "Project path [$PROJECT_PATH]: " CUSTOM_PATH
if [ -n "$CUSTOM_PATH" ]; then
    PROJECT_PATH="$CUSTOM_PATH"
fi

# Expand ~ if present
PROJECT_PATH="${PROJECT_PATH/#\~/$HOME}"
# Remove trailing slash
PROJECT_PATH="${PROJECT_PATH%/}"

echo ""
echo "Project: $PROJECT_NAME"
echo "Location: $PROJECT_PATH"
echo ""

# 4. Copy bridge files to deployment
echo "Copying Engine files..."
mkdir -p "$PROJECT_PATH/Engine"
cp "$ENGINE_DIR/import_step.py" "$PROJECT_PATH/Engine/"
cp "$ENGINE_DIR/reload_assembly.py" "$PROJECT_PATH/Engine/"
cp "$ENGINE_DIR/watcher.py" "$PROJECT_PATH/Engine/"
cp "$ENGINE_DIR/start_watcher.sh" "$PROJECT_PATH/Engine/"
chmod +x "$PROJECT_PATH/Engine/start_watcher.sh"
echo "  Engine files deployed to: $PROJECT_PATH/Engine/"
echo ""

# 5. Create folder structure
PROJECT_FOLDER="$PROJECT_PATH"
PARTS_FOLDER="$PROJECT_PATH/02 - Converted FreeCAD Parts"
VERSIONBACKUP_FOLDER="$PROJECT_PATH/03 - Version Backup"
STEP_FOLDER="$PROJECT_PATH/01 - Drop STEP Files Here"

echo "Creating folders..."
mkdir -p "$PROJECT_FOLDER"
mkdir -p "$PARTS_FOLDER"
mkdir -p "$VERSIONBACKUP_FOLDER"
mkdir -p "$STEP_FOLDER"

# 6. Write FreeCAD trigger file
TRIGGER_FILE="$PROJECT_FOLDER/.reload_trigger"
touch "$TRIGGER_FILE"

# 7. Write FreeCAD trigger config
FREECAD_TRIGGER_CONFIG="$HOME/.freecad_bridge_trigger"
echo -n "$TRIGGER_FILE" > "$FREECAD_TRIGGER_CONFIG"

echo "Trigger file: $TRIGGER_FILE"
echo ""

# 8. Write project config
WATCH_FOLDER="$STEP_FOLDER"

ASSEMBLY_FILE="$PROJECT_FOLDER/$PROJECT_NAME.FCStd"

cat > "$CONFIG_PATH" <<EOF
{
  "watch_folder": "$WATCH_FOLDER",
  "parts_folder": "$PARTS_FOLDER",
  "versionbackup_folder": "$VERSIONBACKUP_FOLDER",
  "fcbak_folder": "$VERSIONBACKUP_FOLDER",
  "reload_trigger_file": "$TRIGGER_FILE",
  "assembly_file": "$ASSEMBLY_FILE",
  "state_file": "$PROJECT_FOLDER/.import_state.json",
  "freecad_lib": "/home/uli/squashfs-root/usr/lib",
  "freecad_python": "/home/uli/squashfs-root/usr/bin/python",
  "import_script": "$PROJECT_FOLDER/Engine/import_step.py"
}
EOF

echo "Config written to: $CONFIG_PATH"
echo ""

# 9. Install macro to FreeCAD
mkdir -p "$FREECAD_MACRO_DIR"
cp "$ENGINE_DIR/reload_assembly.py" "$FREECAD_MACRO_DIR/"

echo "Macro installed to: $FREECAD_MACRO_DIR/reload_assembly.py"
echo ""

# 10. Optional steps
echo "--- Optional Setup Steps ---"
echo ""
echo "  [1] Auto-start FreeCAD + open Assembly workbench"
echo "      + run reload_assembly macro"
echo ""
echo "  [2] Create Plasticity/ folder (for .Plasticity source files)"
echo ""
echo "  [3] Create FreeCAD/ folder (for extra FreeCAD files)"
echo ""
read -rp $'Enter choices (space-separated, e.g. "1 2 3" or Enter to skip): ' OPT_CHOICES

echo ""

if [ -n "$OPT_CHOICES" ]; then
    # Option 1: Auto-start FreeCAD
    if [[ " $OPT_CHOICES " == *" 1 "* ]]; then
        echo "[1] Auto-start FreeCAD..."
        if pgrep -f "AppRun.*freecad" > /dev/null 2>&1 || pgrep -f "freecad" > /dev/null 2>&1; then
            echo "  FreeCAD is already running — skipping launch."
        else
            INIT_DIR="/tmp/freecad_bridge_mod_${PROJECT_NAME// /_}"
            rm -rf "$INIT_DIR"
            MODULE_DIR="$INIT_DIR/FreeCADBridgeInit"
            mkdir -p "$MODULE_DIR"

            cat > "$MODULE_DIR/InitGui.py" << PYEOF
import FreeCAD as App
import FreeCADGui as Gui
import os
from PySide import QtCore

def bridge_startup():
    assembly_path = "${ASSEMBLY_FILE}"
    if os.path.exists(assembly_path) and not App.ActiveDocument:
        App.openDocument(assembly_path)
    Gui.activateWorkbench("Assembly")
    macro_path = "${FREECAD_MACRO_DIR}/reload_assembly.py"
    if os.path.exists(macro_path):
        exec(compile(open(macro_path).read(), macro_path, 'exec'))
    import shutil
    shutil.rmtree("${INIT_DIR}", ignore_errors=True)

QtCore.QTimer.singleShot(3000, bridge_startup)
PYEOF

            echo "  Starting FreeCAD..."
            "$FREECAD_APPIMAGE" -M "$INIT_DIR" "$ASSEMBLY_FILE" &
            sleep 3
            echo "  FreeCAD launched with Assembly workbench + reload_assembly macro."
        fi
        echo ""
    fi

    # Option 2: Plasticity folder
    if [[ " $OPT_CHOICES " == *" 2 "* ]]; then
        echo "[2] Creating Plasticity/ folder..."
        mkdir -p "$PROJECT_FOLDER/Plasticity"
        echo "  Created: $PROJECT_FOLDER/Plasticity/"
        echo ""
    fi

    # Option 3: FreeCAD folder
    if [[ " $OPT_CHOICES " == *" 3 "* ]]; then
        echo "[3] Creating FreeCAD/ folder..."
        mkdir -p "$PROJECT_FOLDER/FreeCAD"
        echo "  Created: $PROJECT_FOLDER/FreeCAD/"
        echo ""
    fi
fi

# 11. Print instructions
echo "=========================================="
echo "  Setup Complete"
echo "=========================================="
echo ""
echo "Folder structure:"
echo "  $PROJECT_FOLDER/"
echo "    Engine/          ← Core scripts (watcher, converter, config, macro)"
echo "    01 - Drop STEP Files Here/  ← Export Plasticity STEP files here"
echo "    02 - Converted FreeCAD Parts/  ← .FCStd files appear here"
echo "    03 - Version Backup/     ← Version history + .FCBak backups (up to 3 per part)"
if [ -d "$PROJECT_FOLDER/Plasticity Source" ]; then
echo "    Plasticity Source/        ← .Plasticity source files"
fi
if [ -d "$PROJECT_FOLDER/FreeCAD Source" ]; then
echo "    FreeCAD Source/           ← Extra FreeCAD files"
fi
echo "    $PROJECT_NAME.FCStd ← Your FreeCAD assembly (save here)"
echo ""
echo "How it works:"
echo "  1. Export part from Plasticity → '01 - Drop STEP Files Here/'"
echo "     → Converted to '02 - Converted FreeCAD Parts/' + backed up in '03 - Version Backup/'"
echo "     → File stays in '01 - Drop STEP Files Here/' (visible for re-save)"
echo "  2. Re-save from Plasticity (Ctrl+S)"
echo "     → Previous version archived in '03 - Version Backup/'"
echo "     → .FCStd re-converted, assembly trigger fired"
echo ""
echo "Next steps:"
echo ""
echo "  1. In FreeCAD: Macro → Macros... → select 'reload_assembly'"
echo "     → click 'Run' (do this once per FreeCAD session)"
echo "  2. Create your assembly in the Assembly workbench"
echo "  3. Add parts from: $PARTS_FOLDER"
echo "  4. Save assembly as: $ASSEMBLY_FILE"
echo "  5. Export parts from Plasticity to '01 - Drop STEP Files Here/' folder"
echo ""

# 12. Ask to start watcher
read -rp "Start the file watcher now? [Y/n]: " START_WATCHER
START_WATCHER="${START_WATCHER:-y}"

if [ "$START_WATCHER" = "y" ] || [ "$START_WATCHER" = "Y" ]; then
    echo ""
    echo "Starting watcher..."
    echo "Watching: $WATCH_FOLDER"
    echo ""
    cd "$PROJECT_FOLDER"
    exec "$VENV_PYTHON" "$PROJECT_FOLDER/Engine/watcher.py"
else
    echo ""
    echo "Watcher not started. Run this to start it manually:"
echo "  $PROJECT_FOLDER/Engine/start_watcher.sh"
echo ""
echo "Or run:"
echo "  cd $PROJECT_FOLDER && $VENV_PYTHON Engine/watcher.py"
fi

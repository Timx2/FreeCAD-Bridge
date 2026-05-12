# Plasticity → FreeCAD Bridge

Watches a `step/` folder for STEP files exported from **Plasticity 3D**, converts them to `.FCStd` files usable in **FreeCAD**, and triggers automatic assembly reload.

## Getting Started

### Linux & macOS

```bash
git clone https://github.com/Timx2/FreeCAD-Bridge.git
cd FreeCAD-Bridge
python3 -m venv venv
source venv/bin/activate
# Run setup — it copies Engine files and creates the project folder
./Engine/setup_project.sh
```

### Windows

```powershell
git clone https://github.com/Timx2/FreeCAD-Bridge.git
cd FreeCAD-Bridge
python -m venv venv
venv\Scripts\activate
# Run the watcher directly (PowerShell):
python Engine/watcher.py --once   # one-shot conversion
python Engine/watcher.py          # continuous watch mode

> **Note:** The `.sh` launcher scripts are Linux/macOS only. On Windows, run `Engine/watcher.py` directly as shown above. The FreeCAD macro (`Engine/reload_assembly.py`) works on all platforms.

## How the Watcher Works

1. **Polling:** The watcher polls `step/` every 2 seconds for new or changed `.step`/`.stp` files.

2. **Save → Convert:** When a STEP file appears (exported from Plasticity), the watcher:
   - **Copies it to `VersionBackup/`** with a timestamp (`PartName_v20260511_120000.step`)
   - **Converts it** to `.FCStd` in `parts/` using FreeCAD's `Part.read()`
   - **Leaves the original file in `step/`** — all part names stay visible in Plasticity's file browser, so you can pick any part to re-save without retyping the name
   - **Writes a trigger file** that tells the FreeCAD macro to reload the assembly

3. **Re-save (Ctrl+S):** When you save again from Plasticity (same or different part), the watcher:
   - **Archives the previous version** to `VersionBackup/` (up to 3 versions per part, oldest auto-pruned)
   - **Re-converts** the updated `.FCStd` in `parts/`
   - Triggers the assembly reload

4. **VersionBackup Pruning:** Only the 3 most recent versions of each part are kept in `VersionBackup/`. Older versions are automatically deleted.

## IMPORTANT: Run the FreeCAD Macro

For automatic assembly reload to work, you must start the `reload_assembly` macro **once per FreeCAD session**:

1. In FreeCAD, go to **Macro → Macros...**
2. Select **reload_assembly** → click **Run**
3. The macro prints `[BridgeReloader] Started` to the report view

This macro watches the trigger file written by the watcher. When a new part is converted, it saves the current assembly, closes it, reopens it, and switches back to the Assembly workbench — so your assembly always reflects the latest parts.

## Folder Structure

```
Project/
  Engine/                         ← Core scripts (watcher, converter, config, macro)
  01 - Drop STEP Files Here/      ← Export Plasticity STEP files here
  02 - Converted FreeCAD Parts/   ← .FCStd files appear here
  03 - Version Backup/            ← Version history + .FCBak backups (up to 3 per part)
  Plasticity Source/              ← [optional] .Plasticity source files
  FreeCAD Source/                 ← [optional] extra FreeCAD files
  .reload_trigger                 ← Trigger file for the FreeCAD macro
  .import_state.json              ← Watcher state (do not edit)
  ProjectName.FCStd               ← Your FreeCAD assembly file
```

## Setup

From the project root, run `Engine/setup_project.sh` — it will:

1. Copy Engine scripts to your deployment folder
2. Ask for a storage disk and project name
3. Create the folder structure
4. Install the `reload_assembly` macro to FreeCAD
5. Offer optional steps:
   - **Auto-start FreeCAD** with Assembly workbench + macro
   - Create `Plasticity/` folder
   - Create `FreeCAD/` folder
6. Start the watcher

## Usage

```
step/  ──►  watcher.py  ──►  parts/ (converted .FCStd)
                  │
                  ├──►  VersionBackup/ (timestamped copies, max 3)
                  │
                  └──►  .reload_trigger ──► FreeCAD macro reloads assembly
```

1. Start the watcher: `Engine/start_watcher.sh` (or `Engine/watcher.py --once` for one-shot)
2. Export a part from Plasticity as STEP to `step/`
3. The part appears in `parts/` as `.FCStd` and the assembly auto-reloads
4. Re-save from Plasticity (Ctrl+S) to archive the previous version and update
5. All part filenames stay visible in `step/` for easy re-selection

### Watcher Options

```
watcher.py [--once] [--force] [--interval <seconds>]

  --once        Process all existing STEP files and exit
  --force       In --once mode, process all files even if unchanged
  --interval    Polling interval in seconds (default: 2)
```

## Files

| File | Purpose |
|------|---------|
| `Engine/watcher.py` | File watcher daemon — polls step/, converts, backs up, triggers reload |
| `Engine/import_step.py` | Standalone STEP → FCStd converter (called by watcher) |
| `Engine/reload_assembly.py` | FreeCAD macro — auto-reloads assembly on trigger |
| `Engine/setup_project.sh` | Interactive project setup |
| `Engine/start_watcher.sh` | Launcher for the watcher daemon |
| `Engine/config.json` | Project configuration (paths) |
| `fix_paths.sh` | Post-disk-rename path fixer |
| `rename_disks.sh` | Disk label rename utility |

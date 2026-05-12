# Plasticity → FreeCAD Bridge

Watches a `step/` folder for STEP files exported from **Plasticity 3D**, converts them to `.FCStd` files usable in **FreeCAD**, and triggers automatic assembly reload.

## Getting Started

### Linux & macOS

```bash
git clone https://github.com/Timx2/FreeCAD-Bridge.git
cd FreeCAD-Bridge
python3 -m venv venv
source venv/bin/activate
# Edit config.json to point at your FreeCAD install
./setup_project.sh
```

### Windows

```powershell
git clone https://github.com/Timx2/FreeCAD-Bridge.git
cd FreeCAD-Bridge
python -m venv venv
venv\Scripts\activate
# Edit config.json to point at your FreeCAD install
# Run the watcher directly (PowerShell):
python watcher.py --once   # one-shot conversion
python watcher.py          # continuous watch mode
```

> **Note:** The `.sh` launcher scripts are Linux/macOS only. On Windows, run `watcher.py` directly as shown above. The FreeCAD macro (`reload_assembly.py`) works on all platforms.

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
  step/              ← Export STEP files from Plasticity here
  parts/             ← Converted .FCStd files land here
  VersionBackup/     ← Version history (up to 3 per part)
    fcbak/           ← .FCBak backups auto-moved here
  Plasticity/        ← [optional] .Plasticity source files
  FreeCAD/           ← [optional] extra FreeCAD files
  .reload_trigger    ← Trigger file for the FreeCAD macro
  .import_state.json ← Watcher state (do not edit)
  ProjectName.FCStd  ← Your FreeCAD assembly file
```

## Setup

Run `setup_project.sh` — it will:

1. Ask for a storage disk and project name
2. Create the folder structure
3. Install the `reload_assembly` macro to FreeCAD
4. Offer optional steps:
   - **Auto-start FreeCAD** with Assembly workbench + macro
   - Create `Plasticity/` folder
   - Create `FreeCAD/` folder
5. Start the watcher

## Usage

```
step/  ──►  watcher.py  ──►  parts/ (converted .FCStd)
                  │
                  ├──►  VersionBackup/ (timestamped copies, max 3)
                  │
                  └──►  .reload_trigger ──► FreeCAD macro reloads assembly
```

1. Start the watcher: `start_watcher.sh` (or `watcher.py --once` for one-shot)
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
| `watcher.py` | File watcher daemon — polls step/, converts, backs up, triggers reload |
| `import_step.py` | Standalone STEP → FCStd converter (called by watcher) |
| `reload_assembly.py` | FreeCAD macro — auto-reloads assembly on trigger |
| `setup_project.sh` | Interactive project setup |
| `start_watcher.sh` | Launcher for the watcher daemon |
| `fix_paths.sh` | Post-disk-rename path fixer |
| `rename_disks.sh` | Disk label rename utility |
| `config.json` | Project configuration (paths) |

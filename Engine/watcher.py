#!/mnt/Disc470/Platicity_tp_FreeCAD/venv/bin/python
import json
import os
import sys
import time
import subprocess
import shutil
import argparse
from functools import partial
from datetime import datetime

print = partial(print, flush=True)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
MAX_VERSIONS = 3


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def get_versionbackup_dir(config):
    vb = config.get("versionbackup_folder")
    if not vb:
        vb = config.get("processed_folder")
    return vb


def convert_step_to_fcstd(config, filepath):
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    fcstd_path = os.path.join(config["parts_folder"], name_no_ext + ".FCStd")

    if os.path.exists(fcstd_path):
        os.remove(fcstd_path)
        time.sleep(0.3)

    env = os.environ.copy()
    env["PYTHONPATH"] = config["freecad_lib"]
    env["LD_LIBRARY_PATH"] = config["freecad_lib"]
    env["CONDA_PREFIX"] = "/home/uli/squashfs-root/usr"

    cmd = [
        config["freecad_python"],
        config["import_script"],
        filepath,
        fcstd_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)

    for line in result.stdout.strip().split("\n"):
        if line:
            print(f"  [FreeCAD] {line}")

    if result.returncode == 0:
        return True, fcstd_path
    else:
        for line in result.stderr.strip().split("\n"):
            if line:
                print(f"  [FreeCAD ERROR] {line}")
        return False, None


def copy_to_version_backup(filepath, versionbackup_dir):
    os.makedirs(versionbackup_dir, exist_ok=True)

    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    ext = os.path.splitext(basename)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name_no_ext}_v{timestamp}{ext}"
    backup_path = os.path.join(versionbackup_dir, backup_name)

    try:
        shutil.copy2(filepath, backup_path)
        print(f"  Backed up to: VersionBackup/{backup_name}")
        return backup_name
    except OSError as e:
        print(f"  Warning: Could not backup file: {e}")
        return None


def prune_version_backup(versionbackup_dir, base_name, max_versions=MAX_VERSIONS):
    if not os.path.isdir(versionbackup_dir):
        return

    matching = []
    for f in os.listdir(versionbackup_dir):
        if f.startswith(base_name + "_v") and f.lower().endswith((".step", ".stp")):
            path = os.path.join(versionbackup_dir, f)
            try:
                matching.append((os.path.getmtime(path), f, path))
            except OSError:
                continue

    matching.sort(key=lambda x: x[0], reverse=True)

    if len(matching) > max_versions:
        removed = 0
        for _, name, path in matching[max_versions:]:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
        if removed:
            print(f"  Pruned {removed} old version(s) of {base_name}")


def cleanup_fcbak_files(watch_folder, fcbak_dir):
    os.makedirs(fcbak_dir, exist_ok=True)

    moved = 0
    for f in sorted(os.listdir(watch_folder)):
        if f.endswith(".FCBak") or f.endswith(".fcbak"):
            src = os.path.join(watch_folder, f)
            try:
                if os.path.getsize(src) == 0:
                    continue
            except OSError:
                continue

            name, ext = os.path.splitext(f)
            dest = os.path.join(fcbak_dir, f)
            if os.path.exists(dest):
                dest = os.path.join(fcbak_dir, f"{name}_{int(time.time())}{ext}")
            try:
                shutil.move(src, dest)
                moved += 1
            except OSError:
                pass

    if moved:
        print(f"  Moved {moved} backup(s) to fcbak/")


def write_reload_trigger(config):
    trigger_path = config.get("reload_trigger_file",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".reload_trigger")
    )
    try:
        with open(trigger_path, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass


def process_step(config, state, name, filepath, stat, state_file, versionbackup_dir, fcbak_dir):
    name_no_ext = os.path.splitext(name)[0]
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Detected: {name}")

    copy_to_version_backup(filepath, versionbackup_dir)
    prune_version_backup(versionbackup_dir, name_no_ext)

    print("  Converting to .FCStd...")

    success, fcstd_path = convert_step_to_fcstd(config, filepath)

    if success:
        state[name] = {"mtime": stat.st_mtime, "size": stat.st_size}
        save_state(state_file, state)
        parts_name = os.path.basename(config.get("parts_folder", "parts"))
        print(f"  Updated {parts_name}/{name_no_ext}.FCStd")
        print(f"  File remains in step/ for re-save access")
        fcbak_dir_actual = fcbak_dir or os.path.join(versionbackup_dir, "fcbak")
        cleanup_fcbak_files(config["watch_folder"], fcbak_dir_actual)
        write_reload_trigger(config)
    else:
        print(f"  FAILED: Conversion error for {name}")


def main():
    parser = argparse.ArgumentParser(description="Watch for STEP files and convert to .FCStd")
    parser.add_argument("--once", action="store_true", help="Process existing files and exit")
    parser.add_argument("--force", action="store_true", help="In --once mode, reprocess all files regardless of state")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default: 2)")
    args = parser.parse_args()

    config = load_config()
    watch_folder = config["watch_folder"]
    parts_folder = config["parts_folder"]
    versionbackup_dir = get_versionbackup_dir(config)
    fcbak_dir = config.get("fcbak_folder", "")
    state_file = config["state_file"]

    os.makedirs(parts_folder, exist_ok=True)
    if versionbackup_dir:
        os.makedirs(versionbackup_dir, exist_ok=True)
    if fcbak_dir:
        os.makedirs(fcbak_dir, exist_ok=True)

    state = load_state(state_file)

    if args.once:
        step_files = []
        for f in os.listdir(watch_folder):
            if f.lower().endswith((".step", ".stp")):
                filepath = os.path.join(watch_folder, f)
                try:
                    stat = os.stat(filepath)
                    if stat.st_size > 0:
                        step_files.append((f, filepath, stat))
                except OSError:
                    continue

        if not step_files:
            print("No STEP files found in watch folder.")
            if versionbackup_dir and versionbackup_dir != fcbak_dir:
                cleanup_fcbak_files(watch_folder, fcbak_dir or os.path.join(versionbackup_dir, "fcbak"))
            print("\nDone.")
            return

        print(f"Found {len(step_files)} STEP file(s) to process.\n")

        if not versionbackup_dir:
            print("ERROR: versionbackup_folder not configured", file=sys.stderr)
            sys.exit(1)

        for name, filepath, stat in sorted(step_files):
            if args.force:
                old = state.pop(name, None)
            process_step(config, state, name, filepath, stat, state_file, versionbackup_dir, fcbak_dir)

        if versionbackup_dir and versionbackup_dir != fcbak_dir:
            cleanup_fcbak_files(watch_folder, fcbak_dir or os.path.join(versionbackup_dir, "fcbak"))

        print("\nDone.")
        return

    if not versionbackup_dir:
        print("ERROR: versionbackup_folder not configured in config.json", file=sys.stderr)
        sys.exit(1)

    print(f"Watching: {watch_folder} (polling every {args.interval}s)")
    print(f"Output: .FCStd files saved in: {parts_folder}")
    print(f"Version backup: {versionbackup_dir} (max {MAX_VERSIONS} per part)")
    print(f"FCBak files moved to: {fcbak_dir or 'VersionBackup'}")
    print("STEP files stay in step/ for re-save access")
    print("Press Ctrl+C to stop.\n")

    file_cooldowns = {}
    last_fcbak_check = 0

    while True:
        try:
            if not os.path.isdir(watch_folder):
                time.sleep(args.interval)
                continue

            current_files = set()
            for f in os.listdir(watch_folder):
                if f.lower().endswith((".step", ".stp")):
                    current_files.add(f)

            new_or_changed = []
            for name in current_files:
                filepath = os.path.join(watch_folder, name)

                if filepath in file_cooldowns:
                    if time.time() - file_cooldowns[filepath] < 3:
                        continue

                try:
                    stat = os.stat(filepath)
                except OSError:
                    continue

                if stat.st_size == 0:
                    continue

                stored = state.get(name)
                if stored and stored["mtime"] == stat.st_mtime and stored["size"] == stat.st_size:
                    continue

                new_or_changed.append((name, filepath, stat))

            for name, filepath, stat in new_or_changed:
                file_cooldowns[filepath] = time.time()
                process_step(config, state, name, filepath, stat, state_file, versionbackup_dir, fcbak_dir)

            now = time.time()
            if now - last_fcbak_check > 3:
                cleanup_fcbak_files(watch_folder, fcbak_dir or os.path.join(versionbackup_dir, "fcbak"))
                last_fcbak_check = now

            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()

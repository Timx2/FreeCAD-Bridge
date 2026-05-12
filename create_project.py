#!/usr/bin/env python3
"""FreeCAD-Bridge Project Creator GUI (ttkbootstrap)"""
import os
import sys
import json
import subprocess
import shutil
import time
import uuid
from pathlib import Path

VENV_SITE = "/home/uli/FreeCAD-Bridge/venv/lib/python3.14/site-packages"
import tkinter as tk
from tkinter import messagebox, filedialog

HAVE_TTKB = False
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAVE_TTKB = True
except ImportError:
    if os.path.isdir(VENV_SITE):
        sys.path.insert(0, VENV_SITE)
        try:
            import ttkbootstrap as ttk
            from ttkbootstrap.constants import *
            HAVE_TTKB = True
        except ImportError:
            pass

if not HAVE_TTKB:
    import tkinter.ttk as ttk

THEMES = ["superhero", "darkly", "cyborg", "solar", "flatly", "litera", "cosmo", "journal"]

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
FREECAD_APPIMAGE = "/home/uli/squashfs-root/AppRun"
FREECAD_MACRO_DIR = os.path.expanduser("~/.local/share/FreeCAD/v1-1/Macro")


class ProjectCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("FreeCAD-Bridge Project Creator")
        self.root.geometry("640x740")
        self.root.minsize(560, 660)

        if HAVE_TTKB:
            self.current_theme = tk.StringVar(value="superhero")
            self.current_theme.trace_add("write", self.on_theme_change)

        self.mount_points = self.get_mount_points()
        self.setup_ui()

    def get_mount_points(self):
        mount_points = []
        try:
            result = subprocess.run(["lsblk", "-o", "MOUNTPOINT", "-nr"],
                                    capture_output=True, text=True)
            for line in result.stdout.strip().split("\n"):
                mp = line.strip()
                if mp and mp not in ["/", "/boot", "/tmp", "/run", "/home"]:
                    mount_points.append(mp)
        except Exception:
            pass
        if not mount_points:
            mount_points = ["/mnt"]
        return mount_points

    def on_theme_change(self, *args):
        if HAVE_TTKB:
            self.root.style.theme_use(self.current_theme.get())

    def setup_ui(self):
        if HAVE_TTKB:
            s = ttk.Style()
            s.configure("TLabelframe", borderwidth=2, relief="solid")

        head = ttk.Frame(self.root, padding=(20, 10))
        head.pack(fill="x")

        title_row = ttk.Frame(head)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="FreeCAD-Bridge Project Creator",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        if HAVE_TTKB:
            ttk.Combobox(title_row, textvariable=self.current_theme,
                        values=THEMES, state="readonly", width=12).pack(side="right")
        ttk.Label(head, text="Plasticity \u2192 FreeCAD STEP bridge setup",
                 font=("Segoe UI", 10)).pack(anchor="w")

        if HAVE_TTKB:
            warn = ttk.Frame(self.root, padding=(14, 8), bootstyle="warning")
            warn.pack(fill="x", padx=20, pady=(0, 10))
            ttk.Label(warn,
                text="IMPORTANT: Run the 'reload_assembly' macro in FreeCAD once per session\n"
                     "\u2192 Macro \u2192 Macros... \u2192 select reload_assembly \u2192 Run",
                font=("Segoe UI", 9)).pack()
        else:
            warn = tk.Frame(self.root, bg="#fff3cd",
                          highlightbackground="#ffc107", highlightthickness=1, padx=10, pady=6)
            warn.pack(fill="x", padx=20, pady=(0, 10))
            tk.Label(warn,
                text="IMPORTANT: Run the 'reload_assembly' macro in FreeCAD once per session",
                bg="#fff3cd", fg="#856404", font=("Arial", 9)).pack()

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        form = ttk.LabelFrame(main, text="Project Settings")
        form.pack(fill="x")
        fi = ttk.Frame(form, padding=12)
        fi.pack(fill="both", expand=True)

        ttk.Label(fi, text="Project Name:").pack(anchor="w")
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(fi, textvariable=self.name_var)
        name_entry.pack(fill="x", pady=(2, 8))
        name_entry.focus()

        ttk.Label(fi, text="Storage Path:").pack(anchor="w")
        path_row = ttk.Frame(fi)
        path_row.pack(fill="x", pady=(2, 8))
        self.path_var = tk.StringVar(value="")
        ttk.Entry(path_row, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="Browse", command=self.browse_path).pack(side="right", padx=(4, 0))

        if len(self.mount_points) > 1:
            ttk.Label(fi, text="Quick Select:").pack(anchor="w")
            self.mount_var = tk.StringVar()
            mc = ttk.Combobox(fi, textvariable=self.mount_var,
                              values=self.mount_points, state="readonly")
            mc.pack(fill="x", pady=(2, 8))
            mc.bind("<<ComboboxSelected>>", self.on_mount_select)

        ttk.Label(fi, text="Full Path:").pack(anchor="w")
        self.full_path_var = tk.StringVar(value="")
        fg = "#007bff" if HAVE_TTKB else "blue"
        ttk.Label(fi, textvariable=self.full_path_var,
                 foreground=fg,
                 font=("Segoe UI", 9, "bold") if HAVE_TTKB else ("Arial", 9, "bold")
                 ).pack(anchor="w")

        opts = ttk.LabelFrame(main, text="Options")
        opts.pack(fill="x", pady=(10, 0))
        oi = ttk.Frame(opts, padding=12)
        oi.pack(fill="both", expand=True)

        self.start_watcher_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(oi, text="Start watcher after creation",
                       variable=self.start_watcher_var).pack(anchor="w")

        self.systemd_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(oi, text="Enable systemd auto-start",
                       variable=self.systemd_var).pack(anchor="w")

        self.autostart_fc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(oi, text="Auto-start FreeCAD + Assembly + macro",
                       variable=self.autostart_fc_var).pack(anchor="w")

        ttk.Separator(oi, orient="horizontal").pack(fill="x", pady=6)

        self.plasticity_folder_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(oi, text="Create Plasticity/ folder (for .Plasticity files)",
                       variable=self.plasticity_folder_var).pack(anchor="w")

        self.freecad_folder_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(oi, text="Create FreeCAD/ folder (for extra FreeCAD files)",
                       variable=self.freecad_folder_var).pack(anchor="w")

        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(16, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bottom, textvariable=self.status_var,
                 font=("Segoe UI", 9) if HAVE_TTKB else ("Arial", 9)).pack(side="left")

        ttk.Button(bottom, text="Cancel", command=self.root.quit).pack(side="right", padx=(4, 0))
        create_btn = ttk.Button(bottom, text="Create Project", command=self.create_project)
        if HAVE_TTKB:
            create_btn.configure(bootstyle="success")
        create_btn.pack(side="right")

        self.name_var.trace_add("write", self.update_preview)
        self.path_var.trace_add("write", self.update_preview)
        self.update_preview()

    def update_preview(self, *args):
        base = self.path_var.get().strip()
        name = self.name_var.get().strip()
        if base and name:
            self.full_path_var.set(os.path.join(base, name))
        elif base:
            self.full_path_var.set(base + "/<project_name>")
        else:
            self.full_path_var.set("")

    def browse_path(self):
        path = filedialog.askdirectory(initialdir="/mnt")
        if path:
            self.path_var.set(path)

    def on_mount_select(self, event):
        self.path_var.set(self.mount_var.get())

    def create_project(self):
        name = self.name_var.get().strip()
        base_path = self.path_var.get().strip()

        if not name:
            messagebox.showerror("Error", "Please enter a project name")
            return
        if not base_path:
            messagebox.showerror("Error", "Please select a storage location")
            return

        project_path = os.path.join(base_path, name)

        try:
            self.status_var.set("Creating project...")
            self.root.update()

            parts_folder = os.path.join(project_path, "parts")
            versionbackup_folder = os.path.join(project_path, "VersionBackup")
            fcbak_folder = os.path.join(versionbackup_folder, "fcbak")
            step_folder = os.path.join(project_path, "step")

            os.makedirs(project_path, exist_ok=True)
            os.makedirs(parts_folder, exist_ok=True)
            os.makedirs(versionbackup_folder, exist_ok=True)
            os.makedirs(fcbak_folder, exist_ok=True)
            os.makedirs(step_folder, exist_ok=True)

            if self.plasticity_folder_var.get():
                os.makedirs(os.path.join(project_path, "Plasticity"), exist_ok=True)
                print(f"Created Plasticity/ folder")
            if self.freecad_folder_var.get():
                os.makedirs(os.path.join(project_path, "FreeCAD"), exist_ok=True)
                print(f"Created FreeCAD/ folder")

            scripts = ["watcher.py", "import_step.py", "start_watcher.sh",
                       "reload_assembly.py", "config.json", "setup_project.sh"]
            for script in scripts:
                src = os.path.join(BRIDGE_DIR, script)
                dst = os.path.join(project_path, script)
                if os.path.exists(src):
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    else:
                        shutil.copytree(src, dst, dirs_exist_ok=True)

            assembly_file = os.path.join(project_path, f"{name}.FCStd")
            config = {
                "watch_folder": step_folder,
                "parts_folder": parts_folder,
                "versionbackup_folder": versionbackup_folder,
                "fcbak_folder": fcbak_folder,
                "reload_trigger_file": os.path.join(project_path, ".reload_trigger"),
                "assembly_file": assembly_file,
                "state_file": os.path.join(project_path, ".import_state.json"),
                "freecad_lib": "/home/uli/squashfs-root/usr/lib",
                "freecad_python": "/home/uli/squashfs-root/usr/bin/python",
                "import_script": os.path.join(project_path, "import_step.py")
            }
            with open(os.path.join(project_path, "config.json"), "w") as f:
                json.dump(config, f, indent=2)

            open(os.path.join(project_path, ".reload_trigger"), "w").close()

            os.makedirs(FREECAD_MACRO_DIR, exist_ok=True)
            macro_src = os.path.join(project_path, "reload_assembly.py")
            if os.path.exists(macro_src):
                shutil.copy2(macro_src,
                    os.path.join(FREECAD_MACRO_DIR, "reload_assembly.py"))

            if self.systemd_var.get():
                self.enable_systemd_service(name, project_path)

            if self.start_watcher_var.get():
                self.start_watcher(project_path)

            if self.autostart_fc_var.get():
                self.autostart_freecad(project_path, assembly_file)

            summary = (
                f"Project created at:\n{project_path}\n\n"
                f"Folders: step/, parts/, VersionBackup/"
            )
            if self.plasticity_folder_var.get():
                summary += ", Plasticity/"
            if self.freecad_folder_var.get():
                summary += ", FreeCAD/"
            summary += f"\n\nMacro installed: reload_assembly.py"
            summary += f"\nSystemd: {'enabled' if self.systemd_var.get() else 'disabled'}"

            messagebox.showinfo("Success", summary)
            self.status_var.set("Project created successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error: " + str(e))

    def autostart_freecad(self, project_path, assembly_file):
        if not os.path.exists(FREECAD_APPIMAGE):
            self.status_var.set("Warning: FreeCAD AppImage not found, skipping")
            self.root.update()
            return

        result = subprocess.run(["pgrep", "-f", "AppRun.*freecad"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.status_var.set("FreeCAD already running \u2014 skipping launch")
            self.root.update()
            return

        init_tag = uuid.uuid4().hex[:8]
        init_dir = f"/tmp/freecad_bridge_mod_{init_tag}"
        module_dir = os.path.join(init_dir, "FreeCADBridgeInit")
        os.makedirs(module_dir, exist_ok=True)

        init_gui_path = os.path.join(module_dir, "InitGui.py")
        with open(init_gui_path, "w") as f:
            f.write(f'''import FreeCAD as App
import FreeCADGui as Gui
import os
from PySide import QtCore

def bridge_startup():
    assembly_path = "{assembly_file}"
    if os.path.exists(assembly_path) and not App.ActiveDocument:
        App.openDocument(assembly_path)
    Gui.activateWorkbench("Assembly")
    macro_path = "{FREECAD_MACRO_DIR}/reload_assembly.py"
    if os.path.exists(macro_path):
        exec(compile(open(macro_path).read(), macro_path, 'exec'))
    import shutil
    shutil.rmtree("{init_dir}", ignore_errors=True)

QtCore.QTimer.singleShot(3000, bridge_startup)
''')

        self.status_var.set("Launching FreeCAD...")
        self.root.update()

        subprocess.Popen(
            [FREECAD_APPIMAGE, "-M", init_dir, assembly_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        time.sleep(2)

    def enable_systemd_service(self, name, project_path):
        service_name = f"freecad-bridge@{name}.service"
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", service_name], check=False)

    def start_watcher(self, project_path):
        watcher_path = os.path.join(project_path, "watcher.py")
        python_path = "/home/uli/squashfs-root/usr/bin/python"
        if os.path.exists(watcher_path):
            subprocess.Popen(
                [python_path, watcher_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )


if __name__ == "__main__":
    if HAVE_TTKB:
        root = ttk.Window(themename="superhero")
    else:
        root = tk.Tk()
    app = ProjectCreator(root)
    root.mainloop()

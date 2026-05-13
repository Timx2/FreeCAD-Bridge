#!/usr/bin/env python3
"""
FreeCAD Bridge — Unified Project Creator + Watcher Manager
Combines setup_project.sh (create) + project_gui.py (manage watchers).
"""

import sys
import os
import json
import subprocess
import shutil
from datetime import datetime

PROJECTS_FILE = os.path.expanduser("~/.projects/projects.dat")
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHER_PYTHON = "/home/uli/squashfs-root/usr/bin/python"
FREECAD_APPIMAGE = "/home/uli/squashfs-root/AppRun"
FREECAD_MACRO_DIR = os.path.expanduser("~/.local/share/FreeCAD/v1-1/Macro")

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        print("PySide6 or PySide2 required.")
        print("Install: pip install PySide6")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def relative_time(date_str):
    if not date_str:
        return "never"
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - dt).total_seconds()
        if diff < 0:
            return "now"
        if diff < 60:
            return "now"
        if diff < 3600:
            return f"{int(diff / 60)} min ago"
        if diff < 86400:
            return f"{int(diff / 3600)} hours ago"
        return f"{int(diff / 86400)} days ago"
    except ValueError:
        return "never"


def load_projects():
    projects = []
    if not os.path.exists(PROJECTS_FILE):
        return projects
    with open(PROJECTS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            projects.append({
                "id": parts[0],
                "title": parts[1] if len(parts) > 1 else "",
                "path": parts[2] if len(parts) > 2 else "",
                "created": parts[3] if len(parts) > 3 else "",
                "last_used": parts[4] if len(parts) > 4 else "",
            })
    return projects


def save_project(proj):
    projects = load_projects()
    found = False
    for i, p in enumerate(projects):
        if p["id"] == proj["id"]:
            projects[i] = proj
            found = True
            break
    if not found:
        projects.append(proj)
    _write_projects(projects)


def delete_project(pid):
    projects = load_projects()
    projects = [p for p in projects if p["id"] != pid]
    _write_projects(projects)


def _write_projects(projects):
    os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        for p in projects:
            f.write(f"{p['id']}|{p['title']}|{p['path']}|{p['created']}|{p['last_used']}\n")


def next_id():
    projects = load_projects()
    if not projects:
        return 1
    return max(int(p["id"]) for p in projects) + 1


def is_watcher_project(proj):
    return os.path.isfile(os.path.join(proj["path"], "Engine", "watcher.py"))


def watcher_running(proj):
    if not is_watcher_project(proj):
        return False
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"{proj['path']}/Engine/watcher.py"],
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def start_watcher(proj):
    watcher_path = os.path.join(proj["path"], "Engine", "watcher.py")
    if not os.path.isfile(watcher_path):
        return False
    try:
        subprocess.Popen(
            [WATCHER_PYTHON, watcher_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def stop_watcher(proj):
    try:
        result = subprocess.run(
            ["pkill", "-f", f"{proj['path']}/Engine/watcher.py"],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def get_mounts():
    mounts = []
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,FSTYPE,SIZE,MOUNTPOINT", "--noheadings", "-r"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) < 4:
                continue
            mp = parts[3]
            if mp in ("/", "/boot", "/tmp", "/run", "none", "[SWAP]", "/var/log"):
                continue
            if not mp or "/snap/" in mp:
                continue
            mounts.append(f"{parts[0]} ({parts[2]})  →  {mp}")
    except Exception:
        if not mounts:
            mounts.append(f"Home  →  {os.path.expanduser('~')}")
    return mounts


def get_mount_path(display_str):
    return display_str.split("→")[-1].strip()


# ---------------------------------------------------------------------------
# Create Project Dialog
# ---------------------------------------------------------------------------

class CreateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Bridge Project")
        self.setMinimumWidth(560)
        self.result_path = None
        self.result_title = None
        self.result_launch = False
        self.build_ui()

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Create New FreeCAD Bridge Project")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)
        layout.addSpacing(8)

        # Mount point
        layout.addWidget(QtWidgets.QLabel("Storage location:"))
        self.mount_combo = QtWidgets.QComboBox()
        for m in get_mounts():
            self.mount_combo.addItem(m)
        layout.addWidget(self.mount_combo)

        # Project name
        layout.addWidget(QtWidgets.QLabel("Project name:"))
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("e.g. NozzleBracket")
        self.name_edit.textChanged.connect(self.update_path)
        layout.addWidget(self.name_edit)

        # Path display
        layout.addWidget(QtWidgets.QLabel("Project path:"))
        self.path_display = QtWidgets.QLineEdit()
        self.path_display.setReadOnly(True)
        layout.addWidget(self.path_display)

        # Options
        layout.addWidget(QtWidgets.QLabel("Optional:"))
        self.opt_plasticity = QtWidgets.QCheckBox("Create Plasticity Source/ folder")
        self.opt_plasticity.setChecked(True)
        layout.addWidget(self.opt_plasticity)
        self.opt_freecad = QtWidgets.QCheckBox("Create FreeCAD Source/ folder")
        layout.addWidget(self.opt_freecad)
        self.opt_launch_fc = QtWidgets.QCheckBox("Launch FreeCAD after creation (Assembly workbench + auto-reload)")
        layout.addWidget(self.opt_launch_fc)

        layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.create_btn = QtWidgets.QPushButton("Create Project")
        self.create_btn.setDefault(True)
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self.do_create)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

    def update_path(self):
        name = self.name_edit.text().strip()
        self.create_btn.setEnabled(bool(name))
        if name:
            idx = self.mount_combo.currentIndex()
            mp = get_mount_path(self.mount_combo.currentText())
            self.path_display.setText(os.path.join(mp, name))
        else:
            self.path_display.setText("")

    def do_create(self):
        title = self.name_edit.text().strip()
        if not title:
            QtWidgets.QMessageBox.warning(self, "Error", "Project name cannot be empty.")
            return

        idx = self.mount_combo.currentIndex()
        mount_path = get_mount_path(self.mount_combo.currentText())
        project_path = os.path.join(mount_path, title)

        # Check if path already exists
        if os.path.exists(project_path):
            reply = QtWidgets.QMessageBox.question(
                self, "Path exists",
                f"Folder already exists:\n{project_path}\n\nUse it anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        self.result_title = title
        self.result_path = project_path
        self.result_launch = self.opt_launch_fc.isChecked()
        self.accept()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class ProjectModel(QtCore.QAbstractTableModel):
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.projects = projects

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.projects)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 5

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        proj = self.projects[index.row()]
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return proj["title"]
            elif col == 1:
                return relative_time(proj["last_used"])
            elif col == 2:
                return "Yes" if is_watcher_project(proj) else ""
            elif col == 3:
                if is_watcher_project(proj):
                    return "● Running" if watcher_running(proj) else "○ Stopped"
                return ""
            elif col == 4:
                return proj["path"]
        if role == QtCore.Qt.ForegroundRole and col == 3:
            if is_watcher_project(proj) and watcher_running(proj):
                return QtGui.QColor("#00cc66")
            elif is_watcher_project(proj):
                return QtGui.QColor("#999999")
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            headers = ["Project", "Last Used", "Bridge", "Watcher", "Path"]
            if section < len(headers):
                return headers[section]
        return None


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FreeCAD Bridge Manager")
        self.setMinimumSize(960, 540)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QtWidgets.QLabel("FreeCAD Bridge Manager")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        # Table
        self.table = QtWidgets.QTableView()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        # Status bar
        self.status_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_label)

        # Buttons row 1 — project actions
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(8)

        self.btn_create = QtWidgets.QPushButton("Create New Project")
        self.btn_create.clicked.connect(self.create_project)
        self.btn_create.setMinimumHeight(36)
        row1.addWidget(self.btn_create)

        self.btn_delete = QtWidgets.QPushButton("Delete Project")
        self.btn_delete.clicked.connect(self.delete_project)
        self.btn_delete.setMinimumHeight(36)
        self.btn_delete.setEnabled(False)
        row1.addWidget(self.btn_delete)

        self.btn_open = QtWidgets.QPushButton("Open in FreeCAD")
        self.btn_open.clicked.connect(self.open_freecad)
        self.btn_open.setMinimumHeight(36)
        self.btn_open.setEnabled(False)
        row1.addWidget(self.btn_open)

        row1.addStretch()
        layout.addLayout(row1)

        # Buttons row 2 — watcher actions
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(8)

        self.btn_toggle = QtWidgets.QPushButton("Start Watcher")
        self.btn_toggle.clicked.connect(self.toggle_watcher)
        self.btn_toggle.setMinimumHeight(36)
        self.btn_toggle.setEnabled(False)
        row2.addWidget(self.btn_toggle)

        self.btn_start_all = QtWidgets.QPushButton("Start All")
        self.btn_start_all.clicked.connect(self.start_all)
        row2.addWidget(self.btn_start_all)

        self.btn_stop_all = QtWidgets.QPushButton("Stop All")
        self.btn_stop_all.clicked.connect(self.stop_all)
        row2.addWidget(self.btn_stop_all)

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        row2.addWidget(self.btn_refresh)

        row2.addStretch()
        layout.addLayout(row2)

    # ---- Selection ----

    def selected_project(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if idx < len(self.model.projects):
            return self.model.projects[idx]
        return None

    def on_select(self):
        proj = self.selected_project()
        if proj:
            self.btn_delete.setEnabled(True)
            self.btn_open.setEnabled(is_watcher_project(proj))
            if is_watcher_project(proj):
                self.btn_toggle.setEnabled(True)
                self.btn_toggle.setText("Stop Watcher" if watcher_running(proj) else "Start Watcher")
            else:
                self.btn_toggle.setEnabled(False)
                self.btn_toggle.setText("Start Watcher")
        else:
            self.btn_delete.setEnabled(False)
            self.btn_open.setEnabled(False)
            self.btn_toggle.setEnabled(False)

    # ---- Actions ----

    def refresh(self):
        projects = load_projects()
        self.model = ProjectModel(projects, self)
        self.table.setModel(self.model)
        self.table.selectionModel().selectionChanged.connect(self.on_select)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 100)

        bridge_projects = [p for p in projects if is_watcher_project(p)]
        running = sum(1 for p in bridge_projects if watcher_running(p))
        self.status_label.setText(
            f"  {len(projects)} project(s) total  ·  "
            f"{len(bridge_projects)} Bridge deployment(s)  ·  "
            f"{running} watcher(s) running"
        )
        self.on_select()

    def create_project(self):
        dlg = CreateDialog(self)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return

        title = dlg.result_title
        project_path = dlg.result_path
        launch_fc = dlg.result_launch
        self.setEnabled(False)
        self.status_label.setText(f"  Creating project '{title}'...")
        QtWidgets.QApplication.processEvents()

        try:
            self._do_create(title, project_path, dlg.opt_plasticity.isChecked(), dlg.opt_freecad.isChecked())
            if launch_fc:
                self._launch_freecad(project_path, title)
            QtWidgets.QMessageBox.information(self, "Success", f"Project '{title}' created successfully.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to create project:\n{e}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def _do_create(self, title, project_path, with_plasticity, with_freecad):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create folders
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, "Engine"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "01 - Drop STEP Files Here"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "02 - Converted FreeCAD Parts"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "03 - Version Backup"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "03 - Version Backup", "step backups"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "03 - Version Backup", "FCBak"), exist_ok=True)
        if with_plasticity:
            os.makedirs(os.path.join(project_path, "Plasticity Source"), exist_ok=True)
        if with_freecad:
            os.makedirs(os.path.join(project_path, "FreeCAD Source"), exist_ok=True)

        # Copy Engine files
        for fname in ("import_step.py", "reload_assembly.py", "watcher.py", "start_watcher.sh"):
            src = os.path.join(ENGINE_DIR, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(project_path, "Engine", fname))
        # Make start_watcher.sh executable
        sw_path = os.path.join(project_path, "Engine", "start_watcher.sh")
        if os.path.isfile(sw_path):
            os.chmod(sw_path, 0o755)

        # Write trigger file
        trigger_path = os.path.join(project_path, ".reload_trigger")
        open(trigger_path, "w").close()

        # Write trigger config
        trigger_config = os.path.expanduser("~/.freecad_bridge_trigger")
        with open(trigger_config, "w") as f:
            f.write(trigger_path)

        # Write config.json
        config = {
            "watch_folder": os.path.join(project_path, "01 - Drop STEP Files Here"),
            "parts_folder": os.path.join(project_path, "02 - Converted FreeCAD Parts"),
            "versionbackup_folder": os.path.join(project_path, "03 - Version Backup", "step backups"),
            "fcbak_folder": os.path.join(project_path, "03 - Version Backup", "FCBak"),
            "reload_trigger_file": trigger_path,
            "assembly_file": os.path.join(project_path, f"{title}.FCStd"),
            "state_file": os.path.join(project_path, ".import_state.json"),
            "freecad_lib": "/home/uli/squashfs-root/usr/lib",
            "freecad_python": WATCHER_PYTHON,
            "import_script": os.path.join(project_path, "Engine", "import_step.py"),
        }
        with open(os.path.join(project_path, "Engine", "config.json"), "w") as f:
            json.dump(config, f, indent=2)

        # Install macro to FreeCAD
        os.makedirs(FREECAD_MACRO_DIR, exist_ok=True)
        macro_src = os.path.join(ENGINE_DIR, "reload_assembly.py")
        if os.path.isfile(macro_src):
            shutil.copy2(macro_src, os.path.join(FREECAD_MACRO_DIR, "reload_assembly.py"))

        # Register in projects.dat
        proj = {
            "id": str(next_id()),
            "title": title,
            "path": project_path,
            "created": now,
            "last_used": now,
        }
        save_project(proj)

    def delete_project(self):
        proj = self.selected_project()
        if not proj:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Project",
            f"Remove '{proj['title']}' from the project list?\n"
            f"(Files on disk will NOT be deleted.)",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            if watcher_running(proj):
                stop_watcher(proj)
            delete_project(proj["id"])
            self.refresh()

    def _launch_freecad(self, project_path, title):
        assembly = os.path.join(project_path, f"{title}.FCStd")
        project_name_safe = title.replace(" ", "_")
        init_dir = f"/tmp/freecad_bridge_mod_{project_name_safe}"
        module_dir = os.path.join(init_dir, "FreeCADBridgeInit")
        os.makedirs(module_dir, exist_ok=True)

        macro_path = os.path.join(FREECAD_MACRO_DIR, "reload_assembly.py")
        with open(os.path.join(module_dir, "InitGui.py"), "w") as f:
            f.write(f'''import FreeCAD as App
import FreeCADGui as Gui
import os
from PySide import QtCore

def bridge_startup():
    assembly_path = "{assembly}"
    if os.path.exists(assembly_path) and not App.ActiveDocument:
        App.openDocument(assembly_path)
    Gui.activateWorkbench("Assembly")
    macro_path = "{macro_path}"
    if os.path.exists(macro_path):
        exec(compile(open(macro_path).read(), macro_path, 'exec'))
    import shutil
    shutil.rmtree("{init_dir}", ignore_errors=True)

QtCore.QTimer.singleShot(3000, bridge_startup)
''')
        args = [FREECAD_APPIMAGE, "-M", init_dir]
        if os.path.exists(assembly):
            args.append(assembly)
        try:
            subprocess.Popen(args)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to launch FreeCAD:\n{e}")

    def open_freecad(self):
        proj = self.selected_project()
        if not proj:
            return
        self._launch_freecad(proj["path"], proj["title"])

    def toggle_watcher(self):
        proj = self.selected_project()
        if not proj or not is_watcher_project(proj):
            return
        if watcher_running(proj):
            stop_watcher(proj)
        else:
            start_watcher(proj)
        QtCore.QTimer.singleShot(300, self.refresh)

    def start_all(self):
        for proj in load_projects():
            if is_watcher_project(proj) and not watcher_running(proj):
                start_watcher(proj)
        QtCore.QTimer.singleShot(500, self.refresh)

    def stop_all(self):
        for proj in load_projects():
            if is_watcher_project(proj) and watcher_running(proj):
                stop_watcher(proj)
        QtCore.QTimer.singleShot(500, self.refresh)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

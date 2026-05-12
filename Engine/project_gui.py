#!/usr/bin/env python3
"""
FreeCAD Bridge — Project Manager GUI
Double-click to launch. Manages your projects and watchers.
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from functools import partial

PROJECTS_FILE = os.path.expanduser("~/.projects/projects.dat")
WATCHER_PYTHON = "/home/uli/squashfs-root/usr/bin/python"

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        print("PySide6 or PySide2 required.")
        print("Install: pip install PySide6")
        sys.exit(1)


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
                return proj["path"]
            elif col == 2:
                return relative_time(proj["last_used"])
            elif col == 3:
                return "Yes" if is_watcher_project(proj) else ""
            elif col == 4:
                if is_watcher_project(proj):
                    return "● Running" if watcher_running(proj) else "○ Stopped"
                return ""
        if role == QtCore.Qt.ForegroundRole and col == 4:
            if is_watcher_project(proj) and watcher_running(proj):
                return QtGui.QColor("#00cc66")
            elif is_watcher_project(proj):
                return QtGui.QColor("#999999")
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            headers = ["Project", "Path", "Last Used", "Bridge", "Watcher"]
            if section < len(headers):
                return headers[section]
        return None


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FreeCAD Bridge — Project Manager")
        self.setMinimumSize(960, 520)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("FreeCAD Bridge — Project Manager")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.table = QtWidgets.QTableView()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        self.status_label = QtWidgets.QLabel("")
        btn_layout.addWidget(self.status_label, 1)

        btn_layout.addStretch()

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_start_all = QtWidgets.QPushButton("Start All Watchers")
        self.btn_start_all.clicked.connect(self.start_all)
        btn_layout.addWidget(self.btn_start_all)

        self.btn_stop_all = QtWidgets.QPushButton("Stop All Watchers")
        self.btn_stop_all.clicked.connect(self.stop_all)
        btn_layout.addWidget(self.btn_stop_all)

        layout.addLayout(btn_layout)

    def refresh(self):
        projects = load_projects()
        self.model = ProjectModel(projects, self)
        self.table.setModel(self.model)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 320)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 60)

        bridge_projects = [p for p in projects if is_watcher_project(p)]
        running = sum(1 for p in bridge_projects if watcher_running(p))
        self.status_label.setText(
            f"  {len(bridge_projects)} Bridge deployment(s), "
            f"{running} watcher(s) running"
        )

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


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

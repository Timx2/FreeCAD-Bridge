"""FreeCAD Macro: Auto-reload assembly when parts change.
Runs inside FreeCAD GUI. Watches for a .reload_trigger file.
When the trigger changes, saves + closes + reopens the assembly.
Usage: Macro → Macro... → select this file → Run"""

import os
import FreeCAD as App
import FreeCADGui as Gui

from PySide import QtCore

RELOAD_TRIGGER_FILE = None
CHECK_INTERVAL = 2000


class AssemblyReloader:
    def __init__(self, trigger_path):
        self.trigger_path = trigger_path
        self._last_mtime = 0
        self._reloading = False
        self._workbench = "Assembly"
        self._pending_reload = None

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check)
        self.timer.start(CHECK_INTERVAL)
        App.Console.PrintMessage(
            f"[BridgeReloader] Watching: {trigger_path}\n"
        )

    def check(self):
        if self._reloading:
            return

        if not os.path.exists(self.trigger_path):
            return

        try:
            mtime = os.path.getmtime(self.trigger_path)
        except OSError:
            return

        if mtime == self._last_mtime:
            return

        self._last_mtime = mtime
        self._pending_reload = True

        QtCore.QTimer.singleShot(100, self._execute_reload)

    def _execute_reload(self):
        if self._pending_reload is None:
            return
        self._pending_reload = None
        self._reload()

    def _reload(self):
        self._reloading = True
        try:
            doc = App.ActiveDocument
            if not doc:
                App.Console.PrintWarning(
                    "[BridgeReloader] No active document\n"
                )
                return

            filepath = doc.FileName
            if not filepath or not os.path.exists(filepath):
                App.Console.PrintWarning(
                    "[BridgeReloader] Assembly not saved yet\n"
                )
                return

            doc_name = doc.Name

            try:
                self._workbench = Gui.activeWorkbench().name()
            except:
                self._workbench = "Assembly"

            doc.save()

            QtCore.QTimer.singleShot(200, lambda n=doc_name, f=filepath: self._do_close(n, f))

        except Exception as e:
            App.Console.PrintError(f"[BridgeReloader] Error: {e}\n")
            self._reloading = False

    def _do_close(self, doc_name, filepath):
        try:
            App.closeDocument(doc_name)

            QtCore.QTimer.singleShot(500, lambda f=filepath: self._do_open(f))
        except Exception as e:
            App.Console.PrintError(f"[BridgeReloader] Close error: {e}\n")
            self._reloading = False

    def _do_open(self, filepath):
        try:
            new_doc = App.openDocument(filepath)
            if new_doc:
                new_doc.recompute()

            QtCore.QTimer.singleShot(200, self._do_switch_workbench)

        except Exception as e:
            App.Console.PrintError(f"[BridgeReloader] Open error: {e}\n")
            self._reloading = False

    def _do_switch_workbench(self):
        try:
            Gui.activateWorkbench(self._workbench)
        except:
            pass

        App.Console.PrintMessage("[BridgeReloader] Assembly reloaded\n")
        self._reloading = False


def start_reloader():
    global RELOAD_TRIGGER_FILE

    if not RELOAD_TRIGGER_FILE:
        for cfg_path in [
            os.path.expanduser("~/.freecad_bridge_trigger"),
        ]:
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    RELOAD_TRIGGER_FILE = f.read().strip()
                break

    if not RELOAD_TRIGGER_FILE:
        App.Console.PrintError(
            "[BridgeReloader] No trigger file configured\n"
        )
        return

    global _reloader
    _reloader = AssemblyReloader(RELOAD_TRIGGER_FILE)
    App.Console.PrintMessage("[BridgeReloader] Started\n")


start_reloader()

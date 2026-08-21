"""GTK4 / libadwaita front end for parch-grub-fixer."""

import os
import re
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from . import __version__, chroot as chroot_mod
from .actions import ACTION_BOTH, ACTION_REPAIR, ACTION_UPGRADE, run_workflow
from .config import console as cli_console
from .system import detect_parch

APP_ID = "io.parchlinux.ParchGrubFixer"

_ANSI_RE = re.compile(r"\x1b\[[0-9;:?]*[A-Za-z]")

ACTION_CHOICES = (
    (ACTION_REPAIR, "Fix GRUB", "Reinstall GRUB and regenerate grub.cfg"),
    (ACTION_UPGRADE, "Full system upgrade", "Run pacman -Syu inside the installation"),
    (ACTION_BOTH, "Upgrade + Fix GRUB", "Upgrade first, then repair GRUB"),
)


def _gui_stream(command, *, input=None):
    """Run a command forwarding its output through the shared Rich console."""
    proc = subprocess.Popen(
        [str(arg) for arg in command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    if input is not None:
        assert proc.stdin is not None
        proc.stdin.write(input)
        proc.stdin.close()
    assert proc.stdout is not None
    for line in proc.stdout:
        cli_console.print(line.rstrip("\n"))
    proc.stdout.close()
    returncode = proc.wait()
    return subprocess.CompletedProcess(command, returncode)


class _LogWriter:
    """File-like sink for the Rich console; forwards clean lines to the UI."""

    def __init__(self, window):
        self._window = window
        self._pending = ""

    def write(self, text):
        text = _ANSI_RE.sub("", text)
        self._pending += text
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            line = line.strip("\r").rstrip()
            if line:
                GLib.idle_add(self._window.append_log_line, line)
        return len(text)

    def flush(self):
        if self._pending.strip():
            GLib.idle_add(self._window.append_log_line, self._pending.strip())
        self._pending = ""


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Parch GRUB Fixer")
        self.set_default_size(760, 560)

        self._systems = []
        self._system_radios = []
        self._action_radios = []
        self._worker = None
        self._original_console_file = cli_console._file
        self._original_stream = chroot_mod.stream
        self._writer = _LogWriter(self)

        self._title = Adw.WindowTitle(title="Parch GRUB Fixer", subtitle=f"v{__version__}")
        header = Adw.HeaderBar(title_widget=self._title)

        self._toast_overlay = Adw.ToastOverlay()
        self._stack = Adw.ViewStack()
        self._toast_overlay.set_child(self._stack)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._toast_overlay)
        self.set_content(toolbar)

        if os.geteuid() != 0:
            self._build_root_error_page()
            return

        self._build_scan_page()
        self._build_select_page()
        self._build_progress_page()

    # Page construction

    def _build_root_error_page(self):
        page = Adw.StatusPage(
            icon_name="dialog-error-symbolic",
            title="Root privileges required",
            description="This tool needs root to scan disks, mount partitions and run pacman.",
        )
        self._stack.add_titled(page, "error", "Error")
        self._stack.set_visible_child_name("error")

    def _build_scan_page(self):
        page = Adw.StatusPage(
            icon_name="drive-harddisk-symbolic",
            title="Find Parch installations",
            description="Scans your disks for Parch Linux systems that need fixing.",
        )

        self._scan_button = Gtk.Button(label="Scan Disks")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.add_css_class("pill")
        self._scan_button.connect("clicked", self._on_scan_clicked)

        self._scan_spinner = Gtk.Spinner()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_halign(Gtk.Align.CENTER)
        box.append(self._scan_button)
        box.append(self._scan_spinner)

        page.set_child(box)
        self._stack.add_titled(page, "scan", "Scan")

    def _build_select_page(self):
        clamp = Adw.Clamp(maximum_size=600, tightening_threshold=480)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(12)
        content.set_margin_end(12)

        self._system_group = Adw.PreferencesGroup(title="Detected Installations")
        content.append(self._system_group)

        action_group = Adw.PreferencesGroup(title="Action")
        radio = None
        for value, title, subtitle in ACTION_CHOICES:
            radio = self._add_radio_row(action_group, radio, title, subtitle, self._on_action_toggled, value)
            self._action_radios.append((radio, value))
        content.append(action_group)

        self._apply_button = Gtk.Button(label="Apply")
        self._apply_button.add_css_class("suggested-action")
        self._apply_button.add_css_class("pill")
        self._apply_button.set_halign(Gtk.Align.CENTER)
        self._apply_button.connect("clicked", self._on_apply_clicked)
        content.append(self._apply_button)

        clamp.set_child(content)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(clamp)
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._stack.add_titled(scroller, "select", "Select")

    def _build_progress_page(self):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        self._log_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=8,
            right_margin=8,
            top_margin=8,
            bottom_margin=8,
        )
        self._log_view.add_css_class("monospace")
        self._log_view.add_css_class("card")

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self._log_view)
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content.append(scroller)

        self._back_button = Gtk.Button(label="Start Over")
        self._back_button.add_css_class("pill")
        self._back_button.set_halign(Gtk.Align.CENTER)
        self._back_button.set_sensitive(False)
        self._back_button.connect("clicked", self._on_back_clicked)
        content.append(self._back_button)

        self._stack.add_titled(content, "progress", "Progress")

    def _add_radio_row(self, group, radio, title, subtitle, callback, value):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        check = Gtk.CheckButton()
        if radio is not None:
            check.set_group(radio)
        else:
            check.set_active(True)
        check.connect("toggled", callback, value)
        row.add_prefix(check)
        row.set_activatable_widget(check)
        group.add(row)
        return check

    # Scan flow

    def _on_scan_clicked(self, button):
        button.set_sensitive(False)
        self._scan_spinner.start()
        self._title.set_subtitle("Scanning…")
        self._worker = threading.Thread(target=self._scan_work, daemon=True)
        self._worker.start()

    def _scan_work(self):
        try:
            systems = detect_parch()
            GLib.idle_add(self._on_scan_done, systems, None)
        except Exception as exc:
            GLib.idle_add(self._on_scan_done, [], str(exc))

    def _on_scan_done(self, systems, error):
        self._scan_spinner.stop()
        self._scan_button.set_sensitive(True)
        self._worker = None

        if error:
            self._toast("Scan failed")
            self._title.set_subtitle(f"v{__version__}")
            return GLib.SOURCE_REMOVE

        if not systems:
            self._toast("No Parch installations found")
            self._title.set_subtitle(f"v{__version__}")
            return GLib.SOURCE_REMOVE

        self._populate_systems(systems)
        self._stack.set_visible_child_name("select")
        self._title.set_subtitle(f"{len(systems)} found")
        return GLib.SOURCE_REMOVE

    def _populate_systems(self, systems):
        self._systems = systems
        self._system_radios.clear()
        while child := self._system_group.get_first_child():
            self._system_group.remove(child)

        radio = None
        for system in systems:
            radio = self._add_radio_row(
                self._system_group,
                radio,
                system["device"],
                system["fstype"],
                self._on_system_toggled,
                system,
            )
            self._system_radios.append((radio, system))

    # Selection helpers

    def _selected_value(self, radios):
        for check, value in radios:
            if check.get_active():
                return value
        return None

    def _on_system_toggled(self, check, system):
        pass

    def _on_action_toggled(self, check, value):
        pass

    # Run flow

    def _on_apply_clicked(self, button):
        system = self._selected_value(self._system_radios)
        action = self._selected_value(self._action_radios)
        if system is None or action is None:
            return

        action_title = next(t for v, t, _ in ACTION_CHOICES if v == action)
        dialog = Adw.MessageDialog(
            heading="Run this operation?",
            body=(
                f"{action_title} on {system['device']}.\n\n"
                "pacman runs unattended (--noconfirm) and GRUB will be reinstalled."
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.set_close_response("cancel")
        dialog.add_response("run", "Run")
        dialog.set_response_appearance("run", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_confirm_response, system, action)
        dialog.present(self)

    def _on_confirm_response(self, dialog, response, system, action):
        dialog.destroy()
        if response != "run":
            return

        buffer = self._log_view.get_buffer()
        buffer.set_text("")
        self._back_button.set_sensitive(False)
        self._stack.set_visible_child_name("progress")
        self._title.set_subtitle("Working…")

        self._redirect_output()
        self._worker = threading.Thread(
            target=self._run_work, args=(system, action), daemon=True
        )
        self._worker.start()

    def _run_work(self, system, action):
        try:
            run_workflow(system, action)
            GLib.idle_add(self._finish_run, None)
        except Exception as exc:
            GLib.idle_add(self._finish_run, str(exc))

    def _finish_run(self, error):
        self._restore_output()
        self._worker = None
        self._back_button.set_sensitive(True)

        if error:
            self.append_log_line(f"Error: {error}")
            self._toast("Operation failed")
            self._title.set_subtitle("Failed")
        else:
            self._toast("Operation completed successfully")
            self._title.set_subtitle("Finished")
        return GLib.SOURCE_REMOVE

    def _on_back_clicked(self, button):
        button.set_sensitive(False)
        self._stack.set_visible_child_name("select")
        self._title.set_subtitle(f"{len(self._systems)} found")

    # Output redirection

    def _redirect_output(self):
        setattr(cli_console, "_file", self._writer)
        chroot_mod.stream = _gui_stream

    def _restore_output(self):
        setattr(cli_console, "_file", self._original_console_file)
        chroot_mod.stream = self._original_stream
        self._writer.flush()

    # Log view

    def append_log_line(self, line):
        buffer = self._log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), line + "\n", -1)
        self._log_view.scroll_to_mark(buffer.get_insert(), 0.0, True, 0.0, 0.0)
        return GLib.SOURCE_REMOVE

    def _toast(self, title):
        toast = Adw.Toast(title=title)
        toast.set_timeout(4)
        self._toast_overlay.add_toast(toast)


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = MainWindow(self)
        window.present()


def main():
    app = Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

"""Adw.Application: ações globais, CSS, abertura de arquivos e reinício após atualizar."""

import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from core import APP_ID, APP_NAME, APP_VERSION  # noqa: E402
from core import i18n  # noqa: E402
from core.debuglog import log  # noqa: E402

CSS = """
.preview-area { background-color: alpha(@window_fg_color, 0.07); }
.pdf-page {
  background-color: white;
  box-shadow: 0 1px 3px alpha(black, 0.25), 0 0 0 1px alpha(black, 0.06);
}
.zoom-bar { border-radius: 999px; padding: 3px; }
.zoom-bar button { border-radius: 999px; }
.zoom-bar .zoom-level { min-width: 62px; font-feature-settings: "tnum"; }
"""


def log_versions(settings):
    log.debug("%s %s — Python %s, GTK %d.%d.%d, libadwaita %d.%d.%d", APP_NAME, APP_VERSION,
              sys.version.split()[0], Gtk.get_major_version(), Gtk.get_minor_version(),
              Gtk.get_micro_version(), Adw.get_major_version(), Adw.get_minor_version(),
              Adw.get_micro_version())
    log.debug("sessão: XDG_SESSION_TYPE=%s XDG_CURRENT_DESKTOP=%s idioma=%s config=%s",
              os.environ.get("XDG_SESSION_TYPE"), os.environ.get("XDG_CURRENT_DESKTOP"),
              i18n.current_language(), settings.path)


class MDtoPDFApp(Adw.Application):
    def __init__(self, settings):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.settings = settings
        self.window = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(APP_ID)

        provider = Gtk.CssProvider()
        try:
            provider.load_from_string(CSS)  # GTK >= 4.12
        except AttributeError:
            provider.load_from_data(CSS, -1)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        for name, callback, accels in (
            ("quit", lambda *_: self.quit(), ["<primary>q"]),
            ("preferences", self._on_preferences, ["<primary>comma"]),
            ("about", self._on_about, []),
            ("check-updates", self._on_check_updates, []),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
            if accels:
                self.set_accels_for_action(f"app.{name}", accels)

        for action, accels in (
            ("win.open", ["<primary>o"]),
            ("win.export", ["<primary>e"]),
            ("win.paste", ["<primary>v"]),
            ("win.reload", ["<primary>r", "F5"]),
            ("win.toggle-sidebar", ["F9"]),
            ("win.zoom-in", ["<primary>plus", "<primary>equal", "<primary>KP_Add"]),
            ("win.zoom-out", ["<primary>minus", "<primary>KP_Subtract"]),
            ("win.zoom-fit", ["<primary>0", "<primary>KP_0"]),
        ):
            self.set_accels_for_action(action, accels)

    def _ensure_window(self):
        from ui.window import MainWindow

        if self.window is None:
            self.window = MainWindow(self, self.settings)
            if self.settings.get("check_updates"):
                self.window.updates.schedule_auto_check()
        return self.window

    def do_activate(self):
        self._ensure_window().present()

    def do_open(self, files, _n_files, _hint):
        win = self._ensure_window()
        win.present()
        paths = [f.get_path() for f in files if f.get_path()]
        if paths:
            win.open_file(paths[0])

    def do_shutdown(self):
        # Depois de "Reiniciar agora" no atualizador, abre a versão nova.
        if self.window is not None:
            current = self.window.path
            self.window.updates.relaunch_if_requested([str(current)] if current else [])
        Adw.Application.do_shutdown(self)

    def _on_check_updates(self, *_args):
        if self.window:
            self.window.updates.check(manual=True)

    def _on_preferences(self, *_args):
        from ui.dialogs import show_preferences

        if self.window:
            show_preferences(self.window)

    def _on_about(self, *_args):
        from ui.dialogs import show_about

        if self.window:
            show_about(self.window)

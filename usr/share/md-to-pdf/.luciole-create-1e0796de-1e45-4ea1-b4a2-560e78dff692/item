"""Painel lateral com as opções do PDF. Cada mudança é salva e atualiza a prévia."""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from core.i18n import _  # noqa: E402


class OptionsPanel(Gtk.Box):
    def __init__(self, window, on_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = window
        self.settings = window.settings
        self.on_changed = on_changed
        self._loading = False
        self.rows = {}

        page = Adw.PreferencesPage(vexpand=True)
        self.append(page)

        # --- Página
        group = Adw.PreferencesGroup(title=_("Page"))
        self._combo(group, "page_size", _("Paper size"), [
            ("A4", _("A4 (210 × 297 mm)")),
            ("A5", _("A5 (148 × 210 mm)")),
            ("Letter", _("Letter (8.5 × 11 in)")),
            ("Legal", _("Legal (8.5 × 14 in)")),
        ])
        self._switch(group, "landscape", _("Landscape"))
        self._combo(group, "margins", _("Margins"), [
            ("narrow", _("Narrow (12 mm)")),
            ("normal", _("Normal (20 mm)")),
            ("wide", _("Wide (30 mm)")),
        ])
        page.add(group)

        # --- Texto
        group = Adw.PreferencesGroup(title=_("Text"))
        self._combo(group, "style", _("Style"), [
            ("clean", _("Clean (sans-serif)")),
            ("classic", _("Classic (serif, justified)")),
        ])
        size = Adw.SpinRow.new_with_range(8, 18, 0.5)
        size.set_title(_("Font size (pt)"))
        size.set_digits(1)
        size.connect("notify::value", lambda row, _p: self._set("font_size", row.get_value()))
        group.add(size)
        self.rows["font_size"] = size
        page.add(group)

        # --- Conteúdo
        group = Adw.PreferencesGroup(title=_("Content"))
        self._switch(group, "toc", _("Table of contents"),
                     _("Built from the headings, with page numbers"))
        self._switch(group, "page_numbers", _("Page numbers"), _("At the bottom of each page"))
        self._switch(group, "highlight_code", _("Syntax highlighting"),
                     _("Colors code blocks that name a language (```python)"))
        self._switch(group, "h1_page_break", _("Level 1 headings on a new page"))
        page.add(group)

        # --- CSS próprio
        group = Adw.PreferencesGroup(
            title=_("Custom stylesheet"),
            description=_("A CSS file applied on top of the chosen style."))
        self.css_row = Adw.ActionRow(title=_("CSS file"))
        self.css_clear = Gtk.Button(icon_name="edit-clear-symbolic", valign=Gtk.Align.CENTER,
                                    tooltip_text=_("Remove the stylesheet"))
        self.css_clear.add_css_class("flat")
        self.css_clear.connect("clicked", lambda *_a: self._set("extra_css", ""))
        choose = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER,
                            tooltip_text=_("Choose a CSS file"))
        choose.add_css_class("flat")
        choose.connect("clicked", self._choose_css)
        self.css_row.add_suffix(self.css_clear)
        self.css_row.add_suffix(choose)
        group.add(self.css_row)
        page.add(group)

        group = Adw.PreferencesGroup()
        reset = Gtk.Button(label=_("Restore defaults"), halign=Gtk.Align.CENTER)
        reset.add_css_class("pill")
        reset.connect("clicked", self._reset)
        group.add(reset)
        page.add(group)

        self.refresh()

    # ------------------------------------------------------------ construção
    def _combo(self, group, key, title, choices):
        codes = [code for code, _label in choices]
        row = Adw.ComboRow(title=title, model=Gtk.StringList.new([label for _c, label in choices]))
        row.codes = codes
        row.connect("notify::selected",
                    lambda r, _p: self._set(key, r.codes[r.get_selected()]))
        group.add(row)
        self.rows[key] = row

    def _switch(self, group, key, title, subtitle=None):
        row = Adw.SwitchRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        row.connect("notify::active", lambda r, _p: self._set(key, r.get_active()))
        group.add(row)
        self.rows[key] = row

    # ----------------------------------------------------------------- estado
    def refresh(self):
        """Mostra os valores das preferências (sem disparar atualizações)."""
        self._loading = True
        try:
            for key, row in self.rows.items():
                value = self.settings.get(key)
                if isinstance(row, Adw.ComboRow):
                    row.set_selected(row.codes.index(value) if value in row.codes else 0)
                elif isinstance(row, Adw.SwitchRow):
                    row.set_active(bool(value))
                else:
                    row.set_value(float(value))
            css = self.settings.get("extra_css")
            self.css_row.set_subtitle(GLib.markup_escape_text(Path(css).name) if css
                                      else _("None"))
            self.css_clear.set_visible(bool(css))
        finally:
            self._loading = False

    def _set(self, key, value):
        if self._loading or self.settings.get(key) == value:
            return
        self.settings.set(key, value)
        if key == "extra_css":
            self.refresh()
        self.on_changed()

    def _reset(self, *_args):
        self.settings.reset_pdf_options()
        self.refresh()
        self.on_changed()

    def _choose_css(self, *_args):
        dialog = Gtk.FileDialog(title=_("Choose a CSS file"), modal=True)
        css_filter = Gtk.FileFilter(name=_("CSS stylesheets"))
        css_filter.add_pattern("*.css")
        css_filter.add_mime_type("text/css")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(css_filter)
        dialog.set_filters(filters)
        current = self.settings.get("extra_css")
        folder = Path(current).parent if current else self.win.path.parent if self.win.path else None
        if folder and folder.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder)))

        def done(dlg, result):
            try:
                gfile = dlg.open_finish(result)
            except GLib.Error:
                return  # cancelado
            if gfile and gfile.get_path():
                self._set("extra_css", gfile.get_path())

        dialog.open(self.win, None, done)

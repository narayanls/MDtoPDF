"""Janela principal: abrir o Markdown, prévia do PDF, opções e exportação."""

import os
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from core import APP_NAME, converter, pasted  # noqa: E402
from core.debuglog import log  # noqa: E402
from core.i18n import _, ngettext  # noqa: E402

from .options import OptionsPanel  # noqa: E402
from .preview import PdfPreview  # noqa: E402
from .updates import UpdateController  # noqa: E402

RENDER_DELAY_MS = 250        # espera depois de uma mudança antes de gerar a prévia
FILE_CHANGE_DELAY_MS = 400   # editores salvam em várias etapas


def _short_path(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home):] if text == home or text.startswith(home + os.sep) else text


def _spinner():
    if hasattr(Adw, "Spinner"):  # libadwaita >= 1.6
        return Adw.Spinner()
    spinner = Gtk.Spinner()
    spinner.start()
    return spinner


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, settings):
        super().__init__(application=app, title=APP_NAME)
        self.settings = settings
        self.busy = False            # exportando; o atualizador espera para mostrar o diálogo
        self.path = None             # Path do Markdown aberto
        self.is_pasted = False       # o documento veio da área de transferência
        self._monitor = None
        self._render_timer = 0
        self._rendering = False
        self._render_again = False
        self._pdf = None             # último PDF da prévia
        self._pdf_key = None         # (opções, datas dos arquivos) usadas nesse PDF
        self._last_export_dir = {}   # Markdown → pasta da última exportação
        self._doc_title = ""         # título do documento (front matter ou primeiro H1)

        self.set_default_size(settings.get("window_width"), settings.get("window_height"))
        if settings.get("window_maximized"):
            self.maximize()
        self.set_size_request(380, 400)

        self.updates = UpdateController(self)
        self._build_ui()
        self._setup_actions()
        self._setup_drop()
        self._update_recent_menu()
        self._update_title()
        self.connect("close-request", self._on_close_request)

    # =================================================================== UI
    def _build_ui(self):
        header = Adw.HeaderBar()

        self.open_button = Adw.SplitButton(label=_("Open"), action_name="win.open",
                                           tooltip_text=_("Open a Markdown file (Ctrl+O)"))
        self.open_button.set_dropdown_tooltip(_("Recent files"))
        self.recent_menu = Gio.Menu()
        self.open_button.set_menu_model(self.recent_menu)
        header.pack_start(self.open_button)

        self.window_title = Adw.WindowTitle(title=APP_NAME)
        header.set_title_widget(self.window_title)

        menu = Gio.Menu()
        section = Gio.Menu()
        section.append(_("Reload"), "win.reload")
        section.append(_("Open With Another App…"), "win.open-with")
        menu.append_section(None, section)
        section = Gio.Menu()
        section.append(_("Preferences"), "app.preferences")
        section.append(_("Check for updates"), "app.check-updates")
        section.append(_("About MDtoPDF"), "app.about")
        menu.append_section(None, section)
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                     tooltip_text=_("Main menu"), primary=True)
        header.pack_end(menu_button)

        self.sidebar_button = Gtk.ToggleButton(icon_name="sidebar-show-right-symbolic",
                                               tooltip_text=_("PDF options (F9)"))
        header.pack_end(self.sidebar_button)

        self.export_button = Gtk.Button(label=_("Export PDF"), action_name="win.export",
                                        tooltip_text=_("Save the PDF (Ctrl+E)"))
        self.export_button.add_css_class("suggested-action")
        header.pack_end(self.export_button)

        self.spinner = _spinner()
        self.spinner.set_visible(False)
        self.spinner.set_tooltip_text(_("Updating the preview…"))
        header.pack_end(self.spinner)

        # Aviso de erro ou de imagens que não carregaram
        self.banner = Adw.Banner()
        self.banner.connect("button-clicked", self._on_banner_button)
        self._banner_is_error = False

        # Conteúdo: tela inicial ou prévia
        empty = Adw.StatusPage(
            icon_name="x-office-document-symbolic",
            title=_("Open a Markdown file"),
            description=_("Drag a .md file here, click Open or paste Markdown text with "
                          "Ctrl+V. The preview updates by itself whenever the file is saved."),
        )
        open_big = Gtk.Button(label=_("Open File…"), action_name="win.open",
                              halign=Gtk.Align.CENTER)
        open_big.add_css_class("pill")
        open_big.add_css_class("suggested-action")
        paste_big = Gtk.Button(label=_("Paste Text"), action_name="win.paste",
                               halign=Gtk.Align.CENTER,
                               tooltip_text=_("Paste Markdown text from the clipboard (Ctrl+V)"))
        paste_big.add_css_class("pill")
        buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          halign=Gtk.Align.CENTER)
        buttons.append(open_big)
        buttons.append(paste_big)
        empty.set_child(buttons)

        self.preview = PdfPreview()
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(empty, "empty")
        self.stack.add_named(self.preview, "preview")

        self.options = OptionsPanel(self, self._on_options_changed)
        self.split = Adw.OverlaySplitView(
            content=self.stack, sidebar=self.options,
            sidebar_position=Gtk.PackType.END,
            min_sidebar_width=280, max_sidebar_width=360,
            show_sidebar=self.settings.get("show_sidebar"),
        )
        self.split.bind_property("show-sidebar", self.sidebar_button, "active",
                                 GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self.split.connect("notify::show-sidebar", self._on_sidebar_toggled)

        self.toasts = Adw.ToastOverlay(child=self.split)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.add_top_bar(self.banner)
        toolbar.set_content(self.toasts)
        self.set_content(toolbar)

        # Em janelas estreitas, as opções viram um painel por cima da prévia.
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 760sp"))
        breakpoint.add_setter(self.split, "collapsed", True)
        breakpoint.connect("apply", lambda *_a: self.split.set_show_sidebar(False))
        self.add_breakpoint(breakpoint)

    def _setup_actions(self):
        for name, callback in (
            ("open", self._on_open),
            ("export", lambda *_: self.export()),
            ("reload", lambda *_: self.schedule_render(0)),
            ("open-with", self._on_open_with),
            ("toggle-sidebar", lambda *_: self.split.set_show_sidebar(not self.split.get_show_sidebar())),
            ("zoom-in", lambda *_: self.preview.zoom_in()),
            ("zoom-out", lambda *_: self.preview.zoom_out()),
            ("zoom-fit", lambda *_: self.preview.zoom_fit()),
            ("clear-recent", self._on_clear_recent),
            ("paste", self._on_paste),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        recent = Gio.SimpleAction.new("open-recent", GLib.VariantType.new("s"))
        recent.connect("activate", lambda _a, param: self.open_file(param.get_string()))
        self.add_action(recent)
        self._update_actions()

    def _update_actions(self):
        has_doc = self.path is not None
        for name in ("export", "reload", "open-with", "zoom-in", "zoom-out", "zoom-fit"):
            self.lookup_action(name).set_enabled(has_doc and not (name == "export" and self.busy))

    def _setup_drop(self):
        # Arquivos (do gerenciador de arquivos) ou texto (selecionado em outro app)
        target = Gtk.DropTarget.new(GObject.TYPE_NONE, Gdk.DragAction.COPY)
        target.set_gtypes([Gdk.FileList, GObject.TYPE_STRING])
        target.connect("drop", self._on_drop)
        self.add_controller(target)

    def toast(self, text, timeout=3):
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=timeout))

    # ============================================================== arquivos
    def _on_open(self, *_args):
        dialog = Gtk.FileDialog(title=_("Open a Markdown file"), modal=True)
        md_filter = Gtk.FileFilter(name=_("Markdown files"))
        for mime in converter.MARKDOWN_MIME_TYPES:
            md_filter.add_mime_type(mime)
        for suffix in converter.MARKDOWN_SUFFIXES:
            md_filter.add_suffix(suffix[1:])
        all_filter = Gtk.FileFilter(name=_("All files"))
        all_filter.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(md_filter)
        filters.append(all_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(md_filter)

        folder = self.path.parent if self.path else Path(self.settings.get("last_folder") or "")
        if str(folder) not in ("", ".") and folder.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder)))

        def done(dlg, result):
            try:
                gfile = dlg.open_finish(result)
            except GLib.Error:
                return  # cancelado
            if gfile.get_path():
                self.open_file(gfile.get_path())
            else:
                self.toast(_("Only local files can be opened."))

        dialog.open(self, None, done)

    def _on_drop(self, _target, value, _x, _y):
        if isinstance(value, str):
            return self.open_text(value)
        paths = [f.get_path() for f in value.get_files() if f.get_path()]
        if not paths:
            return False
        self.open_file(paths[0])
        return True

    # ------------------------------------------------- área de transferência
    def _on_paste(self, *_args):
        # Ctrl+V num campo de texto (ex.: tamanho da letra) cola no campo, não no app.
        focus = self.get_focus()
        if isinstance(focus, Gtk.Text):
            focus.activate_action("clipboard.paste", None)
            return

        clipboard = self.get_clipboard()
        formats = clipboard.get_formats()
        if formats.contain_gtype(Gdk.FileList):
            clipboard.read_value_async(Gdk.FileList, GLib.PRIORITY_DEFAULT, None,
                                       self._on_clipboard_files)
        else:
            clipboard.read_text_async(None, self._on_clipboard_text)

    def _on_clipboard_files(self, clipboard, result):
        try:
            files = clipboard.read_value_finish(result)
        except GLib.Error as exc:
            self.toast(_("Could not read the clipboard: {error}").format(error=exc.message), 5)
            return
        paths = [f.get_path() for f in files.get_files() if f.get_path()]
        if paths:
            self.open_file(paths[0])
        else:
            self.toast(_("Only local files can be opened."))

    def _on_clipboard_text(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
        except GLib.Error as exc:
            log.debug("área de transferência sem texto: %s", exc.message)
            text = None
        if not text or not text.strip():
            self.toast(_("The clipboard has no text to paste."))
            return
        self.open_text(text)

    def open_text(self, text):
        """Mostra um texto Markdown colado (gravado num arquivo temporário)."""
        if not text.strip():
            return False
        # Um caminho de arquivo copiado como texto abre o próprio arquivo.
        candidate = text.strip()
        if "\n" not in candidate and len(candidate) < 4096:
            if candidate.startswith("file://"):
                candidate = Gio.File.new_for_uri(candidate).get_path() or ""
            path = Path(candidate).expanduser()
            if path.is_absolute() and converter.is_markdown(path) and path.is_file():
                self.open_file(path)
                return True
        try:
            path = pasted.save(text)
        except OSError as exc:
            self.toast(_("Could not save the pasted text: {error}").format(
                error=exc.strerror or exc), 6)
            return False
        log.debug("texto colado salvo em %s (%d caracteres)", path, len(text))
        self.open_file(path)
        return True

    def open_file(self, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            self.toast(_("The file {name} was not found.").format(name=path.name), 5)
            self.settings.remove_recent(path)
            self._update_recent_menu()
            return
        log.debug("abrindo %s", path)
        changed = path != self.path
        self.path = path
        self._pdf = self._pdf_key = None
        self.is_pasted = pasted.is_pasted(path)
        if changed:
            self._doc_title = ""
        if not self.is_pasted:
            self.settings.add_recent(path)
            self.settings.set("last_folder", str(path.parent))
            self._update_recent_menu()
        self._watch(path)
        self._update_title()
        self._update_actions()
        self._hide_banner()
        if changed:
            self.preview.clear()
        self.stack.set_visible_child_name("preview")
        self.schedule_render(0)
        if changed:
            GLib.idle_add(lambda: (self.preview.scroll_to_top(), False)[1])

    def _watch(self, path):
        if self._monitor is not None:
            self._monitor.cancel()
        try:
            self._monitor = Gio.File.new_for_path(str(path)).monitor_file(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
            self._monitor.connect("changed", self._on_file_changed)
        except GLib.Error as exc:
            self._monitor = None
            log.warning("não foi possível acompanhar %s: %s", path, exc.message)

    def _on_file_changed(self, _monitor, _file, _other, event):
        if event in (Gio.FileMonitorEvent.ATTRIBUTE_CHANGED, Gio.FileMonitorEvent.PRE_UNMOUNT):
            return
        log.debug("arquivo mudou (%s)", event.value_nick)
        self.schedule_render(FILE_CHANGE_DELAY_MS)

    def _update_title(self):
        if self.path is None:
            self.window_title.set_title(APP_NAME)
            self.window_title.set_subtitle("")
            self.set_title(APP_NAME)
            return
        name = _("Pasted text") if self.is_pasted else self.path.name
        self.window_title.set_title(name)
        subtitle = _("Clipboard") if self.is_pasted else _short_path(self.path.parent)
        if self.preview.pages:
            n = len(self.preview.pages)
            subtitle += " · " + ngettext("{n} page", "{n} pages", n).format(n=n)
        self.window_title.set_subtitle(subtitle)
        self.set_title(f"{name} — {APP_NAME}")

    def _update_recent_menu(self):
        self.recent_menu.remove_all()
        paste = Gio.Menu()
        paste.append(_("Paste from Clipboard"), "win.paste")
        self.recent_menu.append_section(None, paste)
        files = Gio.Menu()
        recent = [p for p in self.settings.get("recent_files") if isinstance(p, str)]
        for path in recent:
            p = Path(path)
            label = f"{p.name}  —  {_short_path(p.parent)}".replace("_", "__")
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value("win.open-recent", GLib.Variant.new_string(path))
            files.append_item(item)
        if not recent:
            files.append(_("No recent files"), "win.none")
        self.recent_menu.append_section(None, files)
        if recent:
            clear = Gio.Menu()
            clear.append(_("Clear List"), "win.clear-recent")
            self.recent_menu.append_section(None, clear)

    def _on_clear_recent(self, *_args):
        self.settings.set("recent_files", [])
        self._update_recent_menu()

    def _on_open_with(self, *_args):
        if self.path is None:
            return
        launcher = Gtk.FileLauncher(file=Gio.File.new_for_path(str(self.path)))
        if hasattr(launcher, "set_always_ask"):  # GTK >= 4.12: escolher o editor
            launcher.set_always_ask(True)
        launcher.launch(self, None, self._on_launched)

    def _on_launched(self, launcher, result):
        try:
            launcher.launch_finish(result)
        except GLib.Error as exc:
            if not exc.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                self.toast(_("Could not open the file: {error}").format(error=exc.message), 5)

    # ================================================================ prévia
    def _options(self):
        return converter.ExportOptions.from_settings(self.settings)

    def _content_key(self):
        """Identifica o que foi usado no PDF: opções + datas do .md e do CSS próprio."""
        def mtime(p):
            try:
                return os.stat(p).st_mtime_ns
            except OSError:
                return None
        opts = self._options()
        return (opts, mtime(self.path), mtime(opts.extra_css) if opts.extra_css else None)

    def _on_options_changed(self):
        self.schedule_render(RENDER_DELAY_MS)

    def schedule_render(self, delay=RENDER_DELAY_MS):
        if self.path is None:
            return
        if self._render_timer:
            GLib.source_remove(self._render_timer)
        self._render_timer = GLib.timeout_add(delay, self._start_render)

    def _start_render(self):
        self._render_timer = 0
        if self.path is None:
            return False
        if self._rendering:
            self._render_again = True  # gera de novo assim que a atual terminar
            return False
        self._rendering = True
        self.spinner.set_visible(True)
        path, key = self.path, self._content_key()
        fallback = self._fallback_title()

        def worker():
            try:
                pdf, doc = converter.render(path, key[0], fallback)
                result = (pdf, doc.warnings, doc.title, None)
            except converter.ConversionError as exc:
                result = (None, [], "", str(exc))
            except Exception as exc:  # noqa: BLE001
                log.exception("erro inesperado ao gerar a prévia")
                result = (None, [], "", _("Unexpected error: {error}").format(error=exc))
            GLib.idle_add(self._on_rendered, path, key, *result)

        threading.Thread(target=worker, daemon=True).start()
        return False

    def _fallback_title(self):
        return _("Pasted text") if self.is_pasted else None

    def _on_rendered(self, path, key, pdf, warnings, title, error):
        self._rendering = False
        self.spinner.set_visible(False)
        if path != self.path:  # outro arquivo foi aberto nesse meio-tempo
            self._render_again = False
            self.schedule_render(0)
            return False
        if error:
            self._show_banner(error, error=True)
        else:
            try:
                self.preview.load(pdf)
            except GLib.Error as exc:
                self._show_banner(_("Could not show the preview: {error}").format(
                    error=exc.message), error=True)
            else:
                self._pdf, self._pdf_key = pdf, key
                self._doc_title = title
                if warnings:
                    self._show_banner(" ".join(warnings[:3]) + (" …" if len(warnings) > 3 else ""))
                else:
                    self._hide_banner()
            self._update_title()
        if self._render_again:
            self._render_again = False
            self._start_render()
        return False

    def _show_banner(self, text, error=False):
        self._banner_is_error = error
        self.banner.set_title(GLib.markup_escape_text(text))
        self.banner.set_button_label(_("Try Again") if error else _("Hide"))
        self.banner.set_revealed(True)

    def _hide_banner(self):
        self.banner.set_revealed(False)

    def _on_banner_button(self, _banner):
        if self._banner_is_error:
            self.schedule_render(0)
        self._hide_banner()

    # ============================================================= exportar
    def export(self):
        if self.path is None or self.busy:
            return
        dialog = Gtk.FileDialog(title=_("Export PDF"), modal=True)
        pdf_filter = Gtk.FileFilter(name=_("PDF documents"))
        pdf_filter.add_mime_type("application/pdf")
        pdf_filter.add_suffix("pdf")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(pdf_filter)
        dialog.set_filters(filters)
        if self.is_pasted:
            # Texto colado: nome a partir do título, pasta da última vez (ou Documentos)
            documents = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
            default_dir = Path(self.settings.get("last_folder") or documents or Path.home())
            title = "" if self._doc_title == _("Pasted text") else self._doc_title
            name = pasted.file_name_for(title, _("document")) + ".pdf"
        else:
            default_dir = self.path.parent
            name = converter.default_output(self.path).name
        folder = self._last_export_dir.get(self.path, default_dir)
        if folder.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder)))
        dialog.set_initial_name(name)

        source = self.path

        def done(dlg, result):
            try:
                gfile = dlg.save_finish(result)
            except GLib.Error:
                return  # cancelado
            if not gfile.get_path():
                self.toast(_("Choose a folder on this computer."), 5)
                return
            target = Path(gfile.get_path())
            if not target.suffix:
                target = target.with_suffix(".pdf")
            if source == self.path:
                self._export_to(target)

        dialog.save(self, None, done)

    def _export_to(self, target: Path):
        self.busy = True
        self._update_actions()
        self.export_button.set_label(_("Exporting…"))
        source, key = self.path, self._content_key()
        fallback = self._fallback_title()
        cached = self._pdf if self._pdf_key == key else None
        log.debug("exportando %s → %s (%s)", source, target,
                  "prévia reaproveitada" if cached else "gerando de novo")

        def worker():
            try:
                pdf = (cached if cached is not None
                       else converter.render(source, key[0], fallback)[0])
                converter.write_pdf(pdf, target)
                error = None
            except converter.ConversionError as exc:
                error = str(exc)
            except Exception as exc:  # noqa: BLE001
                log.exception("erro inesperado ao exportar")
                error = _("Unexpected error: {error}").format(error=exc)
            GLib.idle_add(self._on_exported, source, target, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_exported(self, source, target, error):
        self.busy = False
        self.export_button.set_label(_("Export PDF"))
        self._update_actions()
        if error:
            self.toast(error, 8)
            return False
        self._last_export_dir[source] = target.parent
        toast = Adw.Toast(title=GLib.markup_escape_text(_("Saved {name}").format(name=target.name)),
                          timeout=6, button_label=_("Open"))
        toast.connect("button-clicked", lambda *_a: self._open_pdf(target))
        self.toasts.add_toast(toast)
        return False

    def _open_pdf(self, target):
        Gtk.FileLauncher(file=Gio.File.new_for_path(str(target))).launch(
            self, None, self._on_launched)

    # ================================================================ janela
    def _on_sidebar_toggled(self, *_args):
        if not self.split.get_collapsed():
            self.settings.set("show_sidebar", self.split.get_show_sidebar())

    def _on_close_request(self, *_args):
        maximized = self.is_maximized()
        self.settings.set("window_maximized", maximized, save=False)
        if not maximized:
            width, height = self.get_default_size()
            self.settings.set("window_width", width, save=False)
            self.settings.set("window_height", height, save=False)
        self.settings.save()
        if self._monitor is not None:
            self._monitor.cancel()
        return False


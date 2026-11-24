"""Prévia do PDF: cada página desenhada pelo Poppler numa Gtk.DrawingArea.

A prévia mostra o próprio PDF gerado pelo WeasyPrint (não uma aproximação em
HTML), então o que aparece aqui é exatamente o que será exportado.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Poppler", "0.18")
from gi.repository import GLib, Gdk, Gtk, Poppler  # noqa: E402

from core.i18n import _  # noqa: E402

PX_PER_PT = 96 / 72          # zoom 100% = tamanho real numa tela de 96 dpi
MARGIN = 28                  # espaço em volta das páginas, em px
ZOOM_STEPS = (0.25, 0.33, 0.5, 0.67, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0)
MAX_FIT_ZOOM = 1.6           # "ajustar à largura" não passa disso em telas largas


class PdfPreview(Gtk.Overlay):
    def __init__(self):
        super().__init__()
        self.document = None
        self.pages = []          # [(Poppler.Page, largura_pt, altura_pt)]
        self.areas = []
        self.zoom = 1.0
        self.fit_width = True

        self.column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                              halign=Gtk.Align.CENTER)
        for side in ("top", "bottom", "start", "end"):
            getattr(self.column, f"set_margin_{side}")(MARGIN)
        self.column.set_margin_bottom(MARGIN + 56)  # não esconder a última página sob a barra

        self.scrolled = Gtk.ScrolledWindow(hexpand=True, vexpand=True, child=self.column)
        self.scrolled.add_css_class("preview-area")
        self.scrolled.get_hadjustment().connect("notify::page-size", self._on_width_changed)
        self.set_child(self.scrolled)

        # Ctrl + roda do mouse muda o zoom
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        scroll.connect("scroll", self._on_scroll)
        self.scrolled.add_controller(scroll)

        self.add_overlay(self._zoom_bar())

    def _zoom_bar(self):
        bar = Gtk.Box(spacing=2, halign=Gtk.Align.CENTER, valign=Gtk.Align.END)
        bar.set_margin_bottom(18)
        bar.add_css_class("osd")
        bar.add_css_class("toolbar")
        bar.add_css_class("zoom-bar")
        bar.append(Gtk.Button(icon_name="zoom-out-symbolic", tooltip_text=_("Zoom out (Ctrl+−)"),
                              action_name="win.zoom-out"))
        self.zoom_button = Gtk.Button(label="100%", tooltip_text=_("Fit to width (Ctrl+0)"),
                                      action_name="win.zoom-fit")
        self.zoom_button.add_css_class("zoom-level")
        bar.append(self.zoom_button)
        bar.append(Gtk.Button(icon_name="zoom-in-symbolic", tooltip_text=_("Zoom in (Ctrl++)"),
                              action_name="win.zoom-in"))
        return bar

    # ---------------------------------------------------------------- conteúdo
    def load(self, pdf: bytes) -> int:
        """Mostra um PDF novo. Reaproveita as páginas existentes para não perder a rolagem."""
        document = Poppler.Document.new_from_bytes(GLib.Bytes.new(pdf), None)
        pages = [document.get_page(i) for i in range(document.get_n_pages())]
        self.document = document
        self.pages = [(page, *page.get_size()) for page in pages]

        while len(self.areas) < len(self.pages):
            area = Gtk.DrawingArea()
            area.add_css_class("pdf-page")
            area.set_draw_func(self._draw, len(self.areas))
            self.column.append(area)
            self.areas.append(area)
        while len(self.areas) > len(self.pages):
            self.column.remove(self.areas.pop())

        self._apply_zoom(keep_position=False)
        for area in self.areas:
            area.queue_draw()
        return len(self.pages)

    def clear(self):
        for area in self.areas:
            self.column.remove(area)
        self.areas, self.pages, self.document = [], [], None

    def scroll_to_top(self):
        self.scrolled.get_vadjustment().set_value(0)

    def _draw(self, _area, cr, width, _height, index):
        if index >= len(self.pages):
            return
        page, page_w, _page_h = self.pages[index]
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        scale = width / page_w
        cr.scale(scale, scale)
        page.render(cr)

    # -------------------------------------------------------------------- zoom
    def _fit_zoom(self):
        if not self.pages:
            return self.zoom
        available = self.scrolled.get_hadjustment().get_page_size() - 2 * MARGIN
        widest = max(w for _p, w, _h in self.pages) * PX_PER_PT
        if available <= 0 or widest <= 0:
            return self.zoom
        return max(ZOOM_STEPS[0], min(MAX_FIT_ZOOM, available / widest))

    def _apply_zoom(self, keep_position=True):
        if self.fit_width:
            self.zoom = self._fit_zoom()
        if keep_position:
            self._keep_position()
        for area, (_page, w, h) in zip(self.areas, self.pages):
            area.set_content_width(max(1, round(w * PX_PER_PT * self.zoom)))
            area.set_content_height(max(1, round(h * PX_PER_PT * self.zoom)))
        self.zoom_button.set_label(f"{round(self.zoom * 100)}%")

    def _keep_position(self):
        """Mantém na tela o mesmo trecho do documento depois de mudar o zoom."""
        vadj = self.scrolled.get_vadjustment()
        upper = vadj.get_upper()
        if upper <= vadj.get_page_size():
            return
        fraction = (vadj.get_value() + vadj.get_page_size() / 2) / upper

        def restore(adj, _pspec):
            adj.disconnect(handler)
            GLib.source_remove(timeout)
            adj.set_value(max(0.0, fraction * adj.get_upper() - adj.get_page_size() / 2))

        def give_up():
            vadj.disconnect(handler)
            return False

        handler = vadj.connect("notify::upper", restore)
        timeout = GLib.timeout_add(500, give_up)

    def _on_width_changed(self, *_args):
        if self.fit_width and self.pages and abs(self._fit_zoom() - self.zoom) > 0.005:
            self._apply_zoom()

    def zoom_in(self):
        self._set_zoom(next((z for z in ZOOM_STEPS if z > self.zoom + 0.001), ZOOM_STEPS[-1]))

    def zoom_out(self):
        self._set_zoom(next((z for z in reversed(ZOOM_STEPS) if z < self.zoom - 0.001),
                            ZOOM_STEPS[0]))

    def zoom_fit(self):
        self.fit_width = True
        self._apply_zoom()

    def _set_zoom(self, zoom):
        self.fit_width = False
        if abs(zoom - self.zoom) > 0.001:
            self.zoom = zoom
            self._apply_zoom()

    def _on_scroll(self, controller, _dx, dy):
        state = controller.get_current_event_state()
        if not state & Gdk.ModifierType.CONTROL_MASK or not self.pages:
            return False
        if dy < 0:
            self.zoom_in()
        elif dy > 0:
            self.zoom_out()
        return True

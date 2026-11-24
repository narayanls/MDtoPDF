"""Preferências em ~/.config/md-to-pdf/settings.json."""

import json
import os

from . import APP_SLUG

# Opções do PDF (as mesmas chaves de converter.ExportOptions).
PDF_DEFAULTS = {
    "page_size": "A4",         # A4 | A5 | Letter | Legal
    "landscape": False,
    "margins": "normal",       # narrow | normal | wide
    "style": "clean",          # clean | classic
    "font_size": 11.0,         # pt
    "toc": False,
    "page_numbers": True,
    "highlight_code": True,
    "h1_page_break": False,
    "extra_css": "",
}

DEFAULTS = {
    **PDF_DEFAULTS,
    "language": "auto",        # auto | pt_BR | en
    "check_updates": True,
    "last_folder": "",
    "recent_files": [],
    "show_sidebar": True,
    "window_width": 1180,
    "window_height": 800,
    "window_maximized": False,
}

MAX_RECENT = 10


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_SLUG)


class Settings:
    def __init__(self, path=None):
        self.path = path or os.path.join(config_dir(), "settings.json")
        self.data = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                stored = json.load(fh)
        except (OSError, ValueError):
            return
        if isinstance(stored, dict):
            for key, value in stored.items():
                if key not in DEFAULTS:
                    continue
                default = DEFAULTS[key]
                if isinstance(default, bool):
                    if isinstance(value, bool):
                        self.data[key] = value
                elif isinstance(default, float) and isinstance(value, (int, float)) \
                        and not isinstance(value, bool):
                    self.data[key] = float(value)
                elif isinstance(value, type(default)):
                    self.data[key] = value

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()

    def reset_pdf_options(self):
        for key, value in PDF_DEFAULTS.items():
            self.data[key] = value
        self.save()

    # ------------------------------------------------------------- recentes
    def add_recent(self, path):
        path = str(path)
        recent = [p for p in self.get("recent_files") if isinstance(p, str) and p != path]
        self.set("recent_files", [path, *recent][:MAX_RECENT])

    def remove_recent(self, path):
        self.set("recent_files", [p for p in self.get("recent_files") if p != str(path)])

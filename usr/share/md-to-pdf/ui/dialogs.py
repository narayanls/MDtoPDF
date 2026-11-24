"""Diálogos: preferências e sobre."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from core import APP_ID, APP_NAME, APP_WEBSITE, updater  # noqa: E402
from core.i18n import _  # noqa: E402

# Adw.PreferencesDialog / AboutDialog existem a partir da libadwaita 1.5.
_HAS_PREFS_DIALOG = hasattr(Adw, "PreferencesDialog")
_HAS_ABOUT_DIALOG = hasattr(Adw, "AboutDialog")


def show_preferences(win):
    settings = win.settings

    if _HAS_PREFS_DIALOG:
        dialog = Adw.PreferencesDialog()
    else:
        dialog = Adw.PreferencesWindow(transient_for=win, modal=True)
    dialog.set_title(_("Preferences"))

    page = Adw.PreferencesPage()

    general = Adw.PreferencesGroup(title=_("Updates"))
    check = Adw.SwitchRow(
        title=_("Check for updates on startup"),
        subtitle=_("Looks for a new release on GitHub when the app opens"),
    )
    check.set_active(settings.get("check_updates"))
    check.connect("notify::active", lambda row, _p: settings.set("check_updates", row.get_active()))
    general.add(check)
    page.add(general)

    lang_group = Adw.PreferencesGroup(title=_("Language"))
    codes = ["auto", "pt_BR", "en"]
    model = Gtk.StringList.new([_("Automatic (system)"), "Português (Brasil)", "English"])
    lang = Adw.ComboRow(title=_("Interface language"), model=model)
    lang.set_subtitle(_("Takes effect after restarting the app"))
    current = settings.get("language")
    lang.set_selected(codes.index(current) if current in codes else 0)
    lang.connect("notify::selected", lambda row, _p: settings.set("language", codes[row.get_selected()]))
    lang_group.add(lang)
    page.add(lang_group)

    dialog.add(page)
    if _HAS_PREFS_DIALOG:
        dialog.present(win)
    else:
        dialog.present()


def show_about(win):
    kwargs = dict(
        application_name=APP_NAME,
        application_icon=APP_ID,
        version=updater.display_version(updater.installed_version()),
        developer_name="narayanls",
        license_type=Gtk.License.GPL_3_0,
        website=APP_WEBSITE,
        issue_url=APP_WEBSITE + "/issues",
        comments=_(
            "Reads Markdown files and exports them as formatted PDFs, "
            "with a live preview of the result."
        ),
    )
    if _HAS_ABOUT_DIALOG:
        about = Adw.AboutDialog(**kwargs)
    else:
        about = Adw.AboutWindow(transient_for=win, modal=True, **kwargs)
    about.add_credit_section(_("Built with"), [
        "WeasyPrint https://weasyprint.org",
        "markdown-it-py https://github.com/executablebooks/markdown-it-py",
        "Poppler https://poppler.freedesktop.org",
        "Pygments https://pygments.org",
    ])
    if _HAS_ABOUT_DIALOG:
        about.present(win)
    else:
        about.present()

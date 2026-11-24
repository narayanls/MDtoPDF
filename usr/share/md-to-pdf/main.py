#!/usr/bin/env python3
"""MDtoPDF: lê arquivos Markdown e exporta o conteúdo formatado em PDF."""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core import APP_NAME, APP_VERSION  # noqa: E402
from core import debuglog, i18n  # noqa: E402
from core.i18n import _  # noqa: E402
from core.settings import Settings  # noqa: E402


def usage():
    return _("""{app} {version}

Usage: md-to-pdf [options] [FILE.md]

  -e, --export FILE.md…  convert to PDF without opening the window
  -o, --output FILE.pdf  output file (with a single input file)
  -d, --debug            detailed log in the terminal and in ~/.cache/md-to-pdf/debug.log
  -v, --version          show the version
  -h, --help             show this help

The PDF options (paper, margins, style…) are the ones chosen in the app.
""").format(app=APP_NAME, version=APP_VERSION)


def parse_args(argv):
    """Separa as opções do app das que vão para o GTK (arquivos a abrir etc.)."""
    opts = {
        "debug": os.environ.get("MDTOPDF_DEBUG", "") not in ("", "0"),
        "export": None,
        "output": None,
        "help": False,
        "version": False,
    }
    rest = [argv[0]]
    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-d", "--debug"):
            opts["debug"] = True
        elif arg in ("-e", "--export"):
            opts["export"] = []
        elif arg in ("-o", "--output") and i + 1 < len(args):
            opts["output"] = args[i + 1]
            i += 1
        elif arg.startswith("--output="):
            opts["output"] = arg.split("=", 1)[1]
        elif arg in ("-v", "--version"):
            opts["version"] = True
        elif arg in ("-h", "--help"):
            opts["help"] = True
        elif opts["export"] is not None and not arg.startswith("-"):
            opts["export"].append(arg)
        else:
            rest.append(arg)
        i += 1
    return opts, rest


def export_cli(files, output, settings):
    """md-to-pdf --export: converte sem interface gráfica."""
    from core import converter

    if not files:
        print(_("No input file. Example: md-to-pdf --export notes.md"), file=sys.stderr)
        return 2
    if output and len(files) > 1:
        print(_("--output only works with a single input file."), file=sys.stderr)
        return 2

    options = converter.ExportOptions.from_settings(settings)
    status = 0
    for name in files:
        target = output or converter.default_output(name)
        try:
            pdf, doc = converter.render(name, options)
            converter.write_pdf(pdf, target)
        except converter.ConversionError as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            status = 1
            continue
        for warning in doc.warnings:
            print(f"{name}: {warning}", file=sys.stderr)
        print(_("Saved {path}").format(path=target))
    return status


def main():
    opts, argv = parse_args(sys.argv)
    debuglog.setup(opts["debug"])
    settings = Settings()
    i18n.set_language(settings.get("language"))

    if opts["version"]:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if opts["help"]:
        print(usage())
        return 0
    if opts["export"] is not None:
        return export_cli(opts["export"], opts["output"], settings)

    # Só aqui o GTK é carregado: a exportação pela linha de comando não precisa dele.
    from ui.application import MDtoPDFApp, log_versions

    log_versions(settings)
    return MDtoPDFApp(settings).run(argv)


if __name__ == "__main__":
    sys.exit(main())

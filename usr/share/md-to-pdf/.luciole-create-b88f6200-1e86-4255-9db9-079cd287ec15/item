"""Log de depuração.

Ativado com `md-to-pdf --debug` (ou MDTOPDF_DEBUG=1). Escreve no terminal
e em ~/.cache/md-to-pdf/debug.log. Sem --debug, só avisos e erros vão
para o terminal.

No modo debug, os avisos do WeasyPrint (CSS não suportado, imagens que não
carregaram…) também vão para o log.
"""

import logging
import os
import sys

from . import APP_SLUG

LOGGER_NAME = "mdtopdf"
log = logging.getLogger(LOGGER_NAME)
_enabled = False
_log_file = None

# Bibliotecas usadas na conversão que escrevem no logging do Python.
_THIRD_PARTY = ("weasyprint", "fontTools")


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, APP_SLUG)


def setup(debug=False):
    global _enabled, _log_file
    _enabled = debug
    log.handlers.clear()
    log.propagate = False
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", "%H:%M:%S")

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    console.setLevel(logging.DEBUG if debug else logging.WARNING)
    log.addHandler(console)

    if debug:
        try:
            os.makedirs(cache_dir(), exist_ok=True)
            _log_file = os.path.join(cache_dir(), "debug.log")
            fh = logging.FileHandler(_log_file, mode="w", encoding="utf-8")
            fh.setFormatter(fmt)
            fh.setLevel(logging.DEBUG)
            log.addHandler(fh)
        except OSError as exc:
            _log_file = None
            log.warning("não foi possível criar o arquivo de log: %s", exc)

    log.setLevel(logging.DEBUG if debug else logging.WARNING)

    # Sem --debug, as mensagens dessas bibliotecas ficam em silêncio (o conversor
    # recolhe as que interessam ao usuário, como imagens que não carregaram).
    for name in _THIRD_PARTY:
        other = logging.getLogger(name)
        other.propagate = False
        for handler in list(other.handlers):
            if not isinstance(handler, logging.NullHandler):
                other.removeHandler(handler)
        if debug:
            other.setLevel(logging.WARNING)
            for handler in log.handlers:
                other.addHandler(handler)

    if debug:
        log.debug("modo debug ativo; log em %s", _log_file or "(só terminal)")


def enabled():
    return _enabled


def log_file():
    return _log_file

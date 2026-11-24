"""Texto colado da área de transferência.

O texto vira um arquivo em ~/.cache/md-to-pdf/pasted/, para seguir o mesmo
caminho de um .md aberto: prévia, recarga ao salvar e "Abrir com outro
aplicativo" para editá-lo. Só os arquivos mais recentes são mantidos.
"""

import re
import time
from pathlib import Path

from .debuglog import cache_dir, log

KEEP = 20
PREFIX = "pasted-"


def pasted_dir() -> Path:
    return Path(cache_dir()) / "pasted"


def is_pasted(path) -> bool:
    try:
        return Path(path).resolve().parent == pasted_dir().resolve()
    except OSError:
        return False


def save(text: str) -> Path:
    """Grava o texto e devolve o caminho. Levanta OSError se não conseguir."""
    folder = pasted_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = folder / f"{PREFIX}{stamp}.md"
    n = 1
    while path.exists():
        n += 1
        path = folder / f"{PREFIX}{stamp}-{n}.md"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
    _cleanup(folder)
    return path


def _cleanup(folder: Path):
    files = sorted(folder.glob(f"{PREFIX}*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[KEEP:]:
        try:
            old.unlink()
        except OSError as exc:
            log.debug("não foi possível apagar %s: %s", old, exc)


def file_name_for(title: str, fallback: str) -> str:
    """Nome de arquivo a partir do título do documento ("Relatório 2026" → "Relatório 2026")."""
    name = re.sub(r'[\x00-\x1f/\\:*?"<>|]+', " ", title or "")
    name = re.sub(r"\s+", " ", name).strip(" .")[:80].strip()
    return name or fallback

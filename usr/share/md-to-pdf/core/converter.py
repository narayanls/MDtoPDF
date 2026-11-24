"""Conversão de Markdown para HTML e PDF (sem dependência de GTK).

  Markdown → HTML  markdown-it-py: CommonMark + tabelas, tachado, notas de rodapé,
                   listas de tarefas, listas de definição, alertas do GitHub
                   (> [!NOTE]) e quebras de página (\\newpage ou <!-- pagebreak -->).
  HTML → PDF       WeasyPrint, com o CSS de core/styles.py.

Os caminhos relativos (imagens, links) são resolvidos a partir da pasta do
arquivo Markdown. Um bloco de metadados no início do arquivo (front matter) é
usado nas propriedades do PDF:

  ---
  title: Relatório
  author: Fulano
  lang: pt-BR
  ---
"""

import html
import importlib.util
import logging
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt
from markdown_it.token import Token

from . import APP_NAME, APP_VERSION, styles
from .debuglog import log
from .i18n import _, current_language

try:
    from mdit_py_plugins.deflist import deflist_plugin
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins.tasklists import tasklists_plugin
except ImportError:  # pacote python-mdit_py_plugins ausente: sem esses recursos
    deflist_plugin = footnote_plugin = tasklists_plugin = None

# Opcional (python-linkify-it-py): transforma URLs soltas no texto em links.
HAS_LINKIFY = importlib.util.find_spec("linkify_it") is not None

MARKDOWN_SUFFIXES = (".md", ".markdown", ".mdown", ".mkd", ".mkdn", ".mdwn", ".mdtxt")
MARKDOWN_MIME_TYPES = ("text/markdown", "text/x-markdown")

PAGE_BREAK_HTML = '<div class="page-break"></div>\n'


class ConversionError(Exception):
    """Falha com mensagem pronta para mostrar ao usuário."""


@dataclass(frozen=True)
class ExportOptions:
    page_size: str = "A4"
    landscape: bool = False
    margins: str = "normal"
    style: str = "clean"
    font_size: float = 11.0
    toc: bool = False
    page_numbers: bool = True
    highlight_code: bool = True
    h1_page_break: bool = False
    extra_css: str = ""

    @classmethod
    def from_settings(cls, settings) -> "ExportOptions":
        return cls(**{f.name: settings.get(f.name) for f in fields(cls)}).normalized()

    def normalized(self) -> "ExportOptions":
        """Troca valores inválidos (settings.json editado à mão) pelo padrão."""
        default = ExportOptions()
        changes = {}
        if self.page_size not in styles.PAGE_SIZES:
            changes["page_size"] = default.page_size
        if self.margins not in styles.MARGINS:
            changes["margins"] = default.margins
        if self.style not in styles.STYLES:
            changes["style"] = default.style
        try:
            size = min(max(float(self.font_size), 6.0), 24.0)
        except (TypeError, ValueError):
            size = default.font_size
        if size != self.font_size:
            changes["font_size"] = size
        return replace(self, **changes) if changes else self


@dataclass
class Document:
    html: str
    title: str
    base_url: str
    warnings: list = field(default_factory=list)


# ------------------------------------------------------------------ leitura
def is_markdown(path) -> bool:
    return Path(path).suffix.lower() in MARKDOWN_SUFFIXES


def read_markdown(path) -> str:
    path = Path(path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ConversionError(_("The file {name} was not found.").format(name=path.name)) from exc
    except OSError as exc:
        raise ConversionError(_("Could not read {name}: {error}").format(
            name=path.name, error=exc.strerror or exc)) from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        log.debug("%s não está em UTF-8; lendo como Windows-1252", path)
        return raw.decode("cp1252", errors="replace")


_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.S)
_META_LINE = re.compile(r"^([A-Za-z][\w-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
_META_ITEM = re.compile(r"^[ \t]+-[ \t]+(.*?)[ \t]*$")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def split_front_matter(text: str) -> tuple[dict, str]:
    """Separa o bloco YAML do início (só pares chave: valor e listas simples)."""
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    meta, last = {}, None
    for line in match.group(1).splitlines():
        item = _META_ITEM.match(line)
        if item and last:
            meta[last] = ", ".join(filter(None, [meta[last], _unquote(item.group(1))]))
            continue
        pair = _META_LINE.match(line)
        if not pair:
            continue
        last = pair.group(1).lower()
        value = pair.group(2)
        if value.startswith("[") and value.endswith("]"):
            value = ", ".join(_unquote(v.strip()) for v in value[1:-1].split(",") if v.strip())
        meta[last] = _unquote(value)
    if not meta:
        return {}, text
    return meta, text[match.end():]


# -------------------------------------------------------- Markdown → HTML
def slugify(text: str) -> str:
    """Âncora no estilo do GitHub: "Visão geral!" → "visão-geral"."""
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def _plain_text(inline: Token) -> str:
    return "".join(child.content for child in inline.children or ()
                   if child.type in ("text", "code_inline")).strip()


def _alert_title(kind: str) -> str:
    return {
        "note": _("Note"),
        "tip": _("Tip"),
        "important": _("Important"),
        "warning": _("Warning"),
        "caution": _("Caution"),
    }[kind]


_ALERT = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][ \t]*", re.I)
_BREAK_TEXT = {"\\newpage", "\\pagebreak"}
_BREAK_COMMENT = re.compile(r"^\s*<!--\s*(?:page-?break|new-?page)\s*-->\s*$", re.I)
_TASK_INPUT = re.compile(r'^<input class="task-list-item-checkbox"[^>]*>$')


def _make_alert(tokens, i) -> Token | None:
    """blockquote que começa com [!NOTE] etc. → alerta; devolve o título a inserir."""
    if i + 3 >= len(tokens) or tokens[i + 1].type != "paragraph_open":
        return None
    inline = tokens[i + 2]
    match = _ALERT.match(inline.content)
    children = inline.children or []
    if not match or not children or children[0].type != "text":
        return None
    kind = match.group(1).lower()

    first = children[0]
    first.content = _ALERT.sub("", first.content, count=1)
    if not first.content:
        children.pop(0)
        if children and children[0].type in ("softbreak", "hardbreak"):
            children.pop(0)
    inline.content = _ALERT.sub("", inline.content, count=1).lstrip("\n")
    if not children:  # o marcador estava sozinho no parágrafo
        tokens[i + 1].hidden = tokens[i + 3].hidden = True

    tokens[i].attrJoin("class", f"markdown-alert markdown-alert-{kind}")
    title = Token("html_block", "", 0)
    title.content = f'<p class="markdown-alert-title">{html.escape(_alert_title(kind))}</p>\n'
    return title


def _postprocess(state):
    """Regra final: âncoras dos títulos, alertas, caixas de tarefa e quebras de página."""
    tokens, out = state.tokens, []
    used, headings = {}, []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            text = _plain_text(tokens[i + 1])
            anchor = tok.attrGet("id")
            if not anchor:
                base = slugify(text) or "section"
                count = used.get(base, 0)
                used[base] = count + 1
                anchor = base if count == 0 else f"{base}-{count}"
                tok.attrSet("id", anchor)
            headings.append((int(tok.tag[1]), text, anchor))
        elif (tok.type == "paragraph_open" and i + 2 < len(tokens)
              and tokens[i + 1].type == "inline"
              and tokens[i + 1].content.strip() in _BREAK_TEXT
              and tokens[i + 2].type == "paragraph_close"):
            brk = Token("html_block", "", 0)
            brk.content = PAGE_BREAK_HTML
            out.append(brk)
            i += 3
            continue
        elif tok.type == "html_block" and _BREAK_COMMENT.match(tok.content):
            tok.content = PAGE_BREAK_HTML
        elif tok.type == "blockquote_open":
            title = _make_alert(tokens, i)
            if title is not None:
                out.append(tok)
                out.append(title)
                i += 1
                continue
        elif tok.type == "inline":
            for child in tok.children or ():
                if child.type == "html_inline" and _TASK_INPUT.match(child.content):
                    checked = ' checked' if 'checked="checked"' in child.content else ""
                    child.content = f'<span class="task-box{checked}"></span>'
        out.append(tok)
        i += 1
    state.tokens = out
    state.env["headings"] = headings


def _highlight(code: str, lang: str, _attrs) -> str:
    """Realce do Pygments; vazio = deixa o markdown-it escrever o bloco sem cores."""
    if not lang:
        return ""
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        return ""
    try:
        lexer = get_lexer_by_name(lang.split()[0], stripnl=False)
    except ClassNotFound:
        return ""
    return highlight(code, lexer, HtmlFormatter(nowrap=True))


def _parser(highlight_code: bool) -> MarkdownIt:
    md = MarkdownIt("commonmark", {
        "html": True,
        "linkify": HAS_LINKIFY,
        "highlight": _highlight if highlight_code else None,
    })
    md.enable(["table", "strikethrough"])
    if HAS_LINKIFY:
        md.enable("linkify")
    if footnote_plugin is not None:
        md.use(footnote_plugin).use(tasklists_plugin).use(deflist_plugin)
    md.core.ruler.push("mdtopdf_postprocess", _postprocess)
    return md


def _toc_html(headings) -> str:
    """Sumário com os títulos; um H1 único é o título do documento e fica de fora."""
    top = 2 if sum(1 for level, _t, _a in headings if level == 1) == 1 else 1
    entries = [(level, text, anchor) for level, text, anchor in headings
               if top <= level <= top + 2 and text]
    if not entries:
        return ""
    items = "\n".join(
        f'<li class="toc-level-{level - top + 1}"><a href="#{html.escape(anchor)}">'
        f"{html.escape(text)}</a></li>"
        for level, text, anchor in entries)
    title = html.escape(_("Contents"))
    return (f'<nav class="toc"><p class="toc-title">{title}</p>\n'
            f"<ul>\n{items}\n</ul></nav>\n")


def _document_language(meta) -> str:
    lang = meta.get("lang") or meta.get("language")
    if lang:
        return lang.replace("_", "-")
    return "pt-BR" if current_language() == "pt_BR" else "en"


def markdown_to_html(text: str, opts: ExportOptions, source=None, fallback_title=None) -> Document:
    """Monta o HTML completo (com CSS) que vira o PDF.

    fallback_title: título do PDF quando o texto não tem title nem H1 (sem ele,
    vale o nome do arquivo).
    """
    meta, body = split_front_matter(text)
    env = {}
    body_html = _parser(opts.highlight_code).render(body, env)
    headings = env.get("headings", [])

    if opts.toc:
        toc = _toc_html(headings)
        # Logo depois do título principal, se o documento começa com um H1.
        if toc and body_html.startswith("<h1") and "</h1>\n" in body_html:
            head, _sep, rest = body_html.partition("</h1>\n")
            body_html = head + "</h1>\n" + toc + rest
        else:
            body_html = toc + body_html

    source = Path(source).resolve() if source else None
    title = (meta.get("title")
             or next((t for level, t, _a in headings if level == 1 and t), "")
             or fallback_title
             or (source.stem if source else APP_NAME))

    head = [
        '<meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        f'<meta name="generator" content="{APP_NAME} {APP_VERSION}">',
    ]
    for key, name in (("author", "author"), ("description", "description"),
                      ("subject", "description"), ("keywords", "keywords"),
                      ("tags", "keywords"), ("date", "dcterms.created")):
        if meta.get(key):
            head.append(f'<meta name="{name}" content="{html.escape(meta[key])}">')

    css = (styles.pygments_css(opts) if opts.highlight_code else "") + styles.stylesheet(opts)
    head.append(f"<style>\n{css}\n</style>")

    warnings = []
    if opts.extra_css:
        extra = Path(opts.extra_css).expanduser()
        if extra.is_file():
            # <link> depois do nosso CSS: as regras do usuário têm prioridade e os
            # url() relativos dentro dele continuam valendo.
            head.append(f'<link rel="stylesheet" href="{html.escape(extra.resolve().as_uri())}">')
        else:
            warnings.append(_("The custom stylesheet {name} was not found.").format(name=extra.name))

    base_dir = source.parent if source else Path.cwd()
    page = (f'<!DOCTYPE html>\n<html lang="{html.escape(_document_language(meta))}">\n'
            f"<head>\n" + "\n".join(head) + "\n</head>\n"
            f'<body>\n{body_html}</body>\n</html>\n')
    return Document(html=page, title=title, base_url=base_dir.as_uri() + "/", warnings=warnings)


# ------------------------------------------------------------- HTML → PDF
_LOCK = threading.Lock()  # uma conversão do WeasyPrint por vez


class _LoadFailures(logging.Handler):
    """Recolhe os avisos do WeasyPrint que interessam ao usuário."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.messages = []

    def emit(self, record):
        msg = str(record.msg)
        if not record.args:
            return
        target = str(record.args[0])
        name = unquote(os.path.basename(urlparse(target).path)) or target
        if msg.startswith("Failed to load image"):
            text = _("Could not load the image {name}.").format(name=name)
        elif msg.startswith("Failed to load stylesheet"):
            text = _("Could not load the stylesheet {name}.").format(name=name)
        else:
            return
        if text not in self.messages:
            self.messages.append(text)


def html_to_pdf(doc: Document) -> bytes:
    try:
        import weasyprint
    except ImportError as exc:
        raise ConversionError(
            _("WeasyPrint is not installed (package python-weasyprint).")) from exc

    failures = _LoadFailures()
    wlog = logging.getLogger("weasyprint")
    with _LOCK:
        wlog.addHandler(failures)
        try:
            return weasyprint.HTML(string=doc.html, base_url=doc.base_url).write_pdf(
                presentational_hints=True)
        except Exception as exc:  # noqa: BLE001 — qualquer falha do WeasyPrint
            log.exception("falha do WeasyPrint")
            raise ConversionError(_("Could not create the PDF: {error}").format(error=exc)) from exc
        finally:
            wlog.removeHandler(failures)
            doc.warnings.extend(m for m in failures.messages if m not in doc.warnings)


def render(source, opts: ExportOptions, fallback_title=None) -> tuple[bytes, Document]:
    """Lê o Markdown e devolve (PDF, documento)."""
    doc = markdown_to_html(read_markdown(source), opts, source, fallback_title)
    return html_to_pdf(doc), doc


def write_pdf(data: bytes, target) -> None:
    """Grava num arquivo temporário e troca no fim, para não deixar um PDF pela metade."""
    target = Path(target)
    try:
        fd, tmp = tempfile.mkstemp(prefix=".md-to-pdf-", suffix=".pdf", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.chmod(tmp, 0o644)  # mkstemp cria com 0600
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise ConversionError(_("Could not save {name}: {error}").format(
            name=target.name, error=exc.strerror or exc)) from exc


def default_output(source) -> Path:
    return Path(source).with_suffix(".pdf")

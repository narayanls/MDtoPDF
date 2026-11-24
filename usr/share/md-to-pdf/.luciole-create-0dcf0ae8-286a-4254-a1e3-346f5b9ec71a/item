"""CSS do PDF (lido pelo WeasyPrint).

Dois estilos:
  clean    sem serifa, parecido com o GitHub
  classic  com serifa, texto justificado e hifenizado, títulos centralizados

Tamanho do papel, margens, tamanho da letra e numeração vêm de ExportOptions.
"""

PAGE_SIZES = ("A4", "A5", "Letter", "Legal")
MARGINS = {
    "narrow": "12mm",
    "normal": "20mm 18mm",
    "wide": "30mm 28mm",
}
STYLES = ("clean", "classic")

# Pilhas de fontes: o fontconfig usa a primeira que existir no sistema.
SANS = '"Noto Sans", "Cantarell", "DejaVu Sans", "Liberation Sans", Arial, sans-serif'
SERIF = '"Noto Serif", "Source Serif 4", "DejaVu Serif", "Liberation Serif", "Times New Roman", serif'
MONO = ('"JetBrains Mono", "Fira Code", "Source Code Pro", "Noto Sans Mono", '
        '"DejaVu Sans Mono", "Liberation Mono", monospace')
# Emojis: não entram nas pilhas acima. O fontconfig já recorre a uma fonte de
# emoji (ex.: noto-fonts-emoji) quando o caractere não existe na fonte do texto;
# listada aqui, ela "rouba" dígitos e colchetes (1. → "1 .").

# Tema do Pygments usado em cada estilo para colorir o código.
PYGMENTS_STYLE = {"clean": "default", "classic": "friendly"}


def _page_rules(opts) -> str:
    size = opts.page_size + (" landscape" if opts.landscape else "")
    footer = ""
    if opts.page_numbers:
        footer = (
            '  @bottom-center { content: counter(page) " / " counter(pages); '
            "font-size: 8.5pt; color: #6e7781; }\n"
        )
    return f"@page {{\n  size: {size};\n  margin: {MARGINS[opts.margins]};\n{footer}}}\n"


BASE = """
html {
  font-family: %(body_font)s;
  font-size: %(font_size)spt;
  line-height: 1.55;
  color: #1f2328;
}
body { margin: 0; }

h1, h2, h3, h4, h5, h6 {
  font-family: %(heading_font)s;
  font-weight: 650;
  line-height: 1.25;
  margin: 1.5em 0 0.6em;
  color: #111418;
  break-after: avoid;
  break-inside: avoid;
}
h1 { font-size: 2em; padding-bottom: 0.25em; border-bottom: 1px solid #d8dee4; }
h2 { font-size: 1.5em; padding-bottom: 0.2em; border-bottom: 1px solid #e6eaef; }
h3 { font-size: 1.25em; }
h4 { font-size: 1.05em; }
h5 { font-size: 0.95em; }
h6 { font-size: 0.9em; color: #59636e; }
body > :first-child { margin-top: 0; }

p, ul, ol, dl, table, pre, blockquote, figure, .markdown-alert { margin: 0 0 0.9em; }
p { orphans: 2; widows: 2; }
a { color: #0969da; text-decoration: none; }
strong { font-weight: 650; }
del { color: #6e7781; }
mark { background: #fff3b0; padding: 0 0.1em; }
sup, sub { line-height: 0; }

ul, ol { padding-left: 1.8em; }
li + li { margin-top: 0.2em; }
li > p { margin: 0.3em 0; }
li > ul, li > ol { margin: 0.2em 0 0; }

dt { font-weight: 650; margin-top: 0.6em; }
dd { margin: 0.1em 0 0.4em 1.6em; }

hr { border: 0; border-top: 1px solid #d0d7de; margin: 1.6em 0; }

img { max-width: 100%%; height: auto; }
p > img:only-child { display: block; margin: 0 auto; }
img, figure, svg { break-inside: avoid; }

blockquote {
  margin-left: 0;
  margin-right: 0;
  padding: 0.1em 1em;
  border-left: 0.25em solid #d0d7de;
  color: #59636e;
}
blockquote > :last-child { margin-bottom: 0.4em; }

/* --- Código ---------------------------------------------------------------- */
code, kbd, samp, pre { font-family: %(mono)s; }
code, kbd, samp { font-size: 0.87em; }
:not(pre) > code {
  background: #eff1f3;
  padding: 0.12em 0.38em;
  border-radius: 4px;
}
kbd {
  padding: 0.1em 0.4em;
  border: 1px solid #d0d7de;
  border-bottom-width: 2px;
  border-radius: 4px;
  background: #f6f8fa;
}
pre {
  font-size: 0.85em;
  line-height: 1.45;
  background: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  padding: 0.75em 1em;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  text-align: left;
  hyphens: manual;
}
pre code { font-size: 1em; background: none; padding: 0; border-radius: 0; }

/* --- Tabelas --------------------------------------------------------------- */
table {
  border-collapse: collapse;
  font-size: 0.93em;
  max-width: 100%%;
}
thead { display: table-header-group; }
tr { break-inside: avoid; }
th, td { border: 1px solid #d0d7de; padding: 0.35em 0.75em; vertical-align: top; }
th { background: #f6f8fa; font-weight: 650; text-align: left; }
tbody tr:nth-child(even) td { background: #fafbfc; }
td, th { hyphens: manual; text-align: inherit; }

/* --- Listas de tarefas ----------------------------------------------------- */
ul.contains-task-list { list-style: none; padding-left: 1.4em; }
li.task-list-item { position: relative; }
.task-box {
  display: inline-block;
  width: 0.8em;
  height: 0.8em;
  margin: 0 0.45em 0 -1.25em;
  border: 1.4px solid #8c959f;
  border-radius: 3px;
  vertical-align: -0.08em;
  font-size: 1em;
  line-height: 0.8em;
  text-align: center;
}
.task-box.checked { background: #0969da; border-color: #0969da; }
.task-box.checked::before {
  content: "✓";
  color: #fff;
  font-size: 0.7em;
  font-weight: bold;
  font-family: "DejaVu Sans", %(body_font)s;
}

/* --- Alertas do GitHub (> [!NOTE]) ----------------------------------------- */
.markdown-alert {
  padding: 0.5em 1em;
  border-left: 0.25em solid #0969da;
  color: inherit;
  font-style: normal;
  break-inside: avoid;
}
.markdown-alert > :last-child { margin-bottom: 0.2em; }
.markdown-alert-title { font-weight: 650; margin-bottom: 0.3em; color: #0969da; }
.markdown-alert-tip { border-left-color: #1a7f37; }
.markdown-alert-tip .markdown-alert-title { color: #1a7f37; }
.markdown-alert-important { border-left-color: #8250df; }
.markdown-alert-important .markdown-alert-title { color: #8250df; }
.markdown-alert-warning { border-left-color: #9a6700; }
.markdown-alert-warning .markdown-alert-title { color: #9a6700; }
.markdown-alert-caution { border-left-color: #cf222e; }
.markdown-alert-caution .markdown-alert-title { color: #cf222e; }

/* --- Notas de rodapé ------------------------------------------------------- */
hr.footnotes-sep { margin: 2em 0 0.8em; width: 30%%; }
section.footnotes { font-size: 0.85em; color: #424a53; }
section.footnotes ol { padding-left: 1.5em; }
.footnote-ref a { text-decoration: none; }
.footnote-backref { font-family: "DejaVu Sans", %(body_font)s; }

/* --- Sumário --------------------------------------------------------------- */
nav.toc { break-after: page; }
nav.toc .toc-title {
  font-family: %(heading_font)s;
  font-size: 1.5em;
  font-weight: 650;
  margin: 0 0 0.8em;
}
nav.toc ul { list-style: none; padding: 0; margin: 0; }
nav.toc li { margin: 0.35em 0; }
nav.toc li.toc-level-1 { font-weight: 650; margin-top: 0.7em; }
nav.toc li.toc-level-2 { padding-left: 1.4em; }
nav.toc li.toc-level-3 { padding-left: 2.8em; font-size: 0.95em; }
nav.toc a { color: inherit; }
nav.toc a::after {
  content: leader(".") " " target-counter(attr(href), page);
  font-weight: normal;
  color: #59636e;
}

/* --- Quebras de página ----------------------------------------------------- */
.page-break { break-after: page; height: 0; margin: 0; }
"""

CLASSIC = """
html { line-height: 1.5; color: #222; }
p, li, dd, blockquote { text-align: justify; hyphens: auto; }
h1, h2, h3, h4, h5, h6 { font-weight: 600; color: #1a1a1a; }
h1 { text-align: center; border-bottom: none; font-size: 2.1em; margin-bottom: 0.9em; }
h2 { border-bottom: none; font-size: 1.45em; }
h3 { font-style: italic; font-weight: 600; }
a { color: #1a4f8b; }
blockquote { font-style: italic; border-left-color: #b9b9b9; color: #444; }
th { background: #f2f0eb; }
tbody tr:nth-child(even) td { background: #faf9f6; }
pre { background: #faf9f6; border-color: #e4e0d8; }
:not(pre) > code { background: #f2f0eb; }
nav.toc .toc-title { text-align: center; }
"""

H1_PAGE_BREAK = """
h1 { break-before: page; }
nav.toc + h1 { break-before: auto; }
"""


def stylesheet(opts) -> str:
    """CSS completo para as opções dadas (sem o CSS do Pygments)."""
    classic = opts.style == "classic"
    values = {
        "body_font": SERIF if classic else SANS,
        "heading_font": SERIF if classic else SANS,
        "mono": MONO,
        "font_size": f"{opts.font_size:g}",
    }
    css = _page_rules(opts) + BASE % values
    if classic:
        css += CLASSIC
    if opts.h1_page_break:
        css += H1_PAGE_BREAK
    return css


def pygments_css(opts) -> str:
    """Cores do realce de sintaxe; vazio se o Pygments não estiver instalado."""
    try:
        from pygments.formatters import HtmlFormatter
        from pygments.util import ClassNotFound
    except ImportError:
        return ""
    try:
        formatter = HtmlFormatter(style=PYGMENTS_STYLE.get(opts.style, "default"))
    except ClassNotFound:
        formatter = HtmlFormatter()
    # Só as regras dos tokens; o fundo e o espaçamento do bloco vêm do nosso CSS.
    rules = [line for line in formatter.get_style_defs("pre > code").splitlines()
             if line.startswith("pre > code .")]
    return "\n".join(rules)

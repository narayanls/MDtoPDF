#!/bin/sh
# build-deb.sh — gera o .deb do MDtoPDF.
# Rode na raiz da pasta do .deb (ex.: ~/Github/md-to-pdf-deb/), onde ficam
# este script, after-install.sh, before-remove.sh e as pastas po/ e usr/
# copiadas do repositório MDtoPDF.
# Requisitos: fpm (sudo gem install fpm) e gettext (sudo apt install gettext).

set -eu

PKGNAME="md-to-pdf"
# A versão vem de APP_VERSION (usr/share/md-to-pdf/core/__init__.py), como no
# PKGBUILD: o pacote e o app nunca ficam com números diferentes.
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' usr/share/md-to-pdf/core/__init__.py)"
# Revisão do pacote (equivale ao pkgrel do Arch): aumente para republicar só
# uma correção do .deb. O atualizador do app também compara a revisão.
REVISION="1"
DEB="${PKGNAME}_${VERSION}-${REVISION}_all.deb"

if [ -z "$VERSION" ]; then
    echo "APP_VERSION não encontrado em usr/share/md-to-pdf/core/__init__.py" >&2
    exit 1
fi
for tool in fpm msgfmt; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Falta o programa: $tool" >&2; exit 1; }
done

# ── 1. Limpa caches de bytecode, compila as traduções e acerta permissões ───
find usr -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find usr -type f -name '*.pyc'       -delete              2>/dev/null || true

# po/*.po → usr/share/locale/<idioma>/LC_MESSAGES/md-to-pdf.mo
rm -rf usr/share/locale
for lang in $(grep -v '^#' po/LINGUAS); do
    dest="usr/share/locale/$lang/LC_MESSAGES"
    mkdir -p "$dest"
    msgfmt --check --output-file="$dest/$PKGNAME.mo" "po/$lang.po"
    echo "  $lang -> $dest/$PKGNAME.mo"
done

# Pastas 755 e arquivos 644, depois repõe +x nos dois executáveis.
find usr -type d -exec chmod 755 {} +
find usr -type f -exec chmod 644 {} +
chmod 755 usr/bin/md-to-pdf
chmod 755 usr/share/md-to-pdf/main.py
chmod 755 after-install.sh before-remove.sh

# ── 2. Remove .deb anterior ──────────────────────────────────────────────────
rm -f "$DEB"

# ── 3. Empacota — aponta direto para usr/ sem staging ───────────────────────
#    -C .   define o diretório raiz como o atual (~/Github/md-to-pdf-deb/)
#    usr/   é o único caminho incluído no pacote
#
#    Versões mínimas: GTK 4.10 (Gtk.FileDialog) e libadwaita 1.4
#    (OverlaySplitView, ToolbarView) → Ubuntu 24.04, Debian 13 ou mais novos.
fpm -s dir -t deb \
    -n "$PKGNAME" \
    -v "$VERSION" \
    --iteration "$REVISION" \
    -a all \
    -C . \
    --description "Lê arquivos Markdown e exporta o conteúdo formatado em PDF (GTK4/Adwaita)" \
    --url "https://github.com/narayanls/MDtoPDF" \
    --maintainer "Narayan Lima da Silva <narayan.song@gmail.com>" \
    --license "GPL-3.0-or-later" \
    --category "text" \
    --no-auto-depends \
    --after-install after-install.sh \
    --before-remove before-remove.sh \
    --depends "python3 (>= 3.10)" \
    --depends "python3-gi" \
    --depends "python3-gi-cairo" \
    --depends "gir1.2-gtk-4.0 (>= 4.10)" \
    --depends "gir1.2-adw-1 (>= 1.4)" \
    --depends "gir1.2-poppler-0.18" \
    --depends "weasyprint" \
    --depends "python3-markdown-it" \
    --depends "python3-mdit-py-plugins" \
    --depends "python3-pygments" \
    --deb-recommends "pkexec | policykit-1" \
    --deb-recommends "fonts-noto-core" \
    --deb-recommends "fonts-noto-color-emoji" \
    --deb-suggests "python3-linkify-it" \
    usr/

echo
echo "Gerado: $DEB"
echo "Instale: sudo apt install ./$DEB"

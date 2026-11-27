#!/bin/sh
# Executado pelo dpkg após instalar (ou atualizar) o md-to-pdf.
chmod 755 /usr/bin/md-to-pdf /usr/share/md-to-pdf/main.py

# Bytecode pré-compilado: o app abre mais rápido, já que o usuário não pode
# gravar o cache em /usr/share. before-remove.sh apaga esses arquivos.
if command -v python3 >/dev/null 2>&1; then
    python3 -m compileall -q /usr/share/md-to-pdf >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

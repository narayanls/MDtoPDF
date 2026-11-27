#!/bin/sh
# Executado pelo dpkg antes de remover (ou atualizar) o md-to-pdf.
# Apaga o bytecode gerado por after-install.sh: ele não pertence ao pacote, e
# sem isso o dpkg deixaria a pasta /usr/share/md-to-pdf para trás.
find /usr/share/md-to-pdf -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
exit 0

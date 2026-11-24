# MDtoPDF

**Português** · [English](README.en.md)

Lê arquivos **Markdown** e exporta o conteúdo formatado em **PDF**. Feito em Python com GTK 4 e libadwaita, para Arch Linux e derivados.

A janela mostra uma **prévia do próprio PDF**, página por página, e ela se atualiza sozinha sempre que o arquivo `.md` é salvo, então dá para escrever no seu editor preferido e acompanhar o resultado ao lado.

Interface em português (pt-BR) e em inglês para sistemas em outros idiomas.


<img width="951" height="1028" alt="satty-20261124-161619" src="https://github.com/user-attachments/assets/4bbf5b18-deaa-4ade-a563-a88d782ca294" />


## Recursos

- Prévia fiel: o que aparece na janela é exatamente o PDF que será exportado.
- Papel A4, A5, Carta ou Ofício, retrato ou paisagem, três tamanhos de margem.
- Dois estilos: **Limpo** (sem serifa, parecido com o GitHub) e **Clássico** (com serifa, justificado e hifenizado).
- Sumário com números de página, numeração no rodapé e marcadores (bookmarks) do PDF a partir dos títulos.
- Realce de sintaxe nos blocos de código.
- Folha de estilo CSS própria, aplicada por cima do estilo escolhido.
- Título, autor e palavras-chave do PDF tirados do front matter.
- Colar texto Markdown da área de transferência (<kbd>Ctrl</kbd>+<kbd>V</kbd>), além de abrir arquivos.
- Exportação pela linha de comando, sem abrir a janela.
- Atualização automática a partir dos Releases do GitHub.

### Markdown suportado

CommonMark com as extensões do GitHub: tabelas, ~~tachado~~, listas de tarefas, notas de rodapé, alertas (`> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`), listas de definição, HTML embutido e emojis. Sublistas com dois espaços funcionam como no GitHub.

Extras para PDF:

- **Quebra de página**: uma linha com `\newpage` (ou `\pagebreak`, ou `<!-- pagebreak -->`).
- **Front matter** no início do arquivo:

  ```yaml
  ---
  title: Relatório anual
  author: Fulano de Tal
  lang: pt-BR
  keywords: [relatório, 2026]
  ---
  ```

  `title` vira o título do PDF; sem ele, vale o primeiro título `#`. `lang` define o idioma usado na hifenização do estilo Clássico.

- Imagens e links relativos são procurados a partir da pasta do arquivo `.md`.

O arquivo [`examples/demo.md`](examples/demo.md) mostra tudo isso.

## Instalação

### Pacote pronto (Arch Linux e derivados)

Funciona no Arch Linux e em derivados como CachyOS, EndeavourOS e Manjaro.

1. Baixe o arquivo `md-to-pdf-<versão>-1-any.pkg.tar.zst` na página de [Releases](https://github.com/narayanls/MDtoPDF/releases/latest).
2. Instale com o pacman, na pasta onde o arquivo foi salvo:

   ```sh
   sudo pacman -U md-to-pdf-1.0.0-1-any.pkg.tar.zst
   ```

O pacman instala as dependências (`python-gobject`, `gtk4`, `libadwaita`, `poppler-glib`, `python-weasyprint`, `python-markdown-it-py`, `python-mdit_py_plugins` e `python-pygments`). Depois, abra o **MDtoPDF** pelo menu de aplicativos ou rode `md-to-pdf` no terminal.

Dependências opcionais: `noto-fonts` (fontes preferidas dos estilos), `noto-fonts-emoji` (emojis coloridos) e `python-linkify-it-py` (transforma URLs soltas em links).

Para remover:

```sh
sudo pacman -R md-to-pdf
```

### Compilar a partir do código-fonte

```sh
git clone https://github.com/narayanls/MDtoPDF.git
cd MDtoPDF/pkgbuild
makepkg -si
```

O `makepkg` gera o mesmo arquivo `.pkg.tar.zst` publicado nos Releases, dentro da pasta `pkgbuild`.

### Rodar sem instalar

```sh
make            # compila as traduções (precisa do pacote gettext)
python3 usr/share/md-to-pdf/main.py
```

Sem o `make`, o app abre em inglês.

## Uso

Abra um arquivo pelo botão **Abrir**, arrastando-o para a janela ou pelo gerenciador de arquivos (**Abrir com → MDtoPDF**). Ajuste as opções no painel lateral e clique em **Exportar PDF**.

Também dá para **colar** um texto Markdown com <kbd>Ctrl</kbd>+<kbd>V</kbd> (ou **Colar texto** na tela inicial, ou no menu do botão Abrir) e arrastar um texto selecionado em outro programa para a janela. O texto colado fica num arquivo temporário em `~/.cache/md-to-pdf/pasted/` (os 20 mais recentes são mantidos); para editá-lo, use **Menu → Abrir com outro aplicativo**, e a prévia acompanha. Imagens com caminho relativo não funcionam em texto colado, porque não há uma pasta de referência; use caminhos absolutos ou URLs. Se o que estiver copiado for um arquivo `.md` (copiado no gerenciador de arquivos), ele é aberto normalmente.

| Atalho | Ação |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>O</kbd> | Abrir arquivo |
| <kbd>Ctrl</kbd>+<kbd>V</kbd> | Colar texto Markdown |
| <kbd>Ctrl</kbd>+<kbd>E</kbd> | Exportar PDF |
| <kbd>Ctrl</kbd>+<kbd>R</kbd> ou <kbd>F5</kbd> | Recarregar (ex.: depois de trocar uma imagem) |
| <kbd>F9</kbd> | Mostrar/ocultar as opções |
| <kbd>Ctrl</kbd>+<kbd>+</kbd> / <kbd>Ctrl</kbd>+<kbd>−</kbd> / <kbd>Ctrl</kbd>+roda do mouse | Zoom |
| <kbd>Ctrl</kbd>+<kbd>0</kbd> | Ajustar à largura |
| <kbd>Ctrl</kbd>+<kbd>,</kbd> | Preferências |

### Linha de comando

```sh
md-to-pdf notas.md                          # abre na janela
md-to-pdf --export notas.md                 # gera notas.pdf ao lado
md-to-pdf --export notas.md -o saida.pdf    # escolhe o arquivo de saída
md-to-pdf --export *.md                     # converte vários de uma vez
md-to-pdf --debug                           # log em ~/.cache/md-to-pdf/debug.log
```

A exportação pela linha de comando usa as mesmas opções escolhidas no app (papel, margens, estilo…).

As preferências ficam em `~/.config/md-to-pdf/settings.json`.

## Atualizações

O app verifica o último release do GitHub ao abrir (dá para desligar em **Menu → Preferências**) e também em **Menu → Verificar atualizações**. Se houver versão nova, mostra as novidades e oferece **Atualizar**: baixa o pacote, confere o tamanho e o SHA-256 informados pelo GitHub e instala com `pkexec pacman -U`, que pede a senha numa janela do sistema. Depois é só reiniciar o app; o arquivo aberto é reaberto na versão nova.

Rodando a partir do código-fonte, o app só avisa da versão nova e aponta para o GitHub.

## 🛠️ Construído com

- [Python 3](https://www.python.org) + [PyGObject](https://pygobject.gnome.org)
- [GTK4](https://gtk.org) + [Adwaita (libadwaita)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- Vibe Coding:
  Claude Sonnet foi usada para geração de código. O programa foi revisado e testado por humano

## Licença

GPL-3.0-or-later. Veja [LICENSE](LICENSE).

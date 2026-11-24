# MDtoPDF

[Português](README.md) · **English**

Reads **Markdown** files and exports the formatted content as **PDF**. Written in Python with GTK 4 and libadwaita, for Arch Linux and derivatives.

The window shows a **preview of the actual PDF**, page by page, and it refreshes by itself whenever the `.md` file is saved, so you can write in your favorite editor and watch the result side by side.

The interface is in English, and in Portuguese (pt-BR) on Portuguese systems.

## Features

- Faithful preview: what you see in the window is exactly the PDF that will be exported.
- A4, A5, Letter or Legal paper, portrait or landscape, three margin sizes.
- Two styles: **Clean** (sans-serif, GitHub-like) and **Classic** (serif, justified and hyphenated).
- Table of contents with page numbers, page numbers in the footer, and PDF bookmarks from the headings.
- Syntax highlighting in code blocks.
- Your own CSS stylesheet, applied on top of the chosen style.
- PDF title, author and keywords taken from the front matter.
- Paste Markdown text from the clipboard (<kbd>Ctrl</kbd>+<kbd>V</kbd>), besides opening files.
- Command-line export, without opening the window.
- Automatic updates from the GitHub Releases.

### Supported Markdown

CommonMark with the GitHub extensions: tables, ~~strikethrough~~, task lists, footnotes, alerts (`> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`), definition lists, inline HTML and emoji. Two-space nested lists work like on GitHub.

PDF extras:

- **Page break**: a line with `\newpage` (or `\pagebreak`, or `<!-- pagebreak -->`).
- **Front matter** at the top of the file:

  ```yaml
  ---
  title: Annual report
  author: Jane Doe
  lang: en
  keywords: [report, 2026]
  ---
  ```

  `title` becomes the PDF title; without it, the first `#` heading is used. `lang` sets the hyphenation language of the Classic style.

- Relative images and links are resolved from the folder of the `.md` file.

The file [`examples/demo.md`](examples/demo.md) shows all of this.

## Installation

### Prebuilt package (Arch Linux and derivatives)

Works on Arch Linux and derivatives such as CachyOS, EndeavourOS and Manjaro.

1. Download `md-to-pdf-<version>-1-any.pkg.tar.zst` from the [Releases](https://github.com/narayanls/MDtoPDF/releases/latest) page.
2. Install it with pacman, from the folder where you saved it:

   ```sh
   sudo pacman -U md-to-pdf-1.0.0-1-any.pkg.tar.zst
   ```

pacman installs the dependencies (`python-gobject`, `gtk4`, `libadwaita`, `poppler-glib`, `python-weasyprint`, `python-markdown-it-py`, `python-mdit_py_plugins` and `python-pygments`). Then open **MDtoPDF** from the application menu or run `md-to-pdf` in a terminal.

Optional: `noto-fonts` (preferred fonts of the styles), `noto-fonts-emoji` (color emoji) and `python-linkify-it-py` (turns bare URLs into links).

To remove it:

```sh
sudo pacman -R md-to-pdf
```

### Build from source

```sh
git clone https://github.com/narayanls/MDtoPDF.git
cd MDtoPDF/pkgbuild
makepkg -si
```

`makepkg` builds the same `.pkg.tar.zst` published in the Releases, inside the `pkgbuild` folder.

### Run without installing

```sh
make            # compiles the translations (needs the gettext package)
python3 usr/share/md-to-pdf/main.py
```

Without `make`, the app opens in English.

## Usage

Open a file with the **Open** button, by dragging it onto the window, or from the file manager (**Open With → MDtoPDF**). Adjust the options in the sidebar and click **Export PDF**.

You can also **paste** Markdown text with <kbd>Ctrl</kbd>+<kbd>V</kbd> (or **Paste Text** on the start screen, or in the Open button menu) and drag selected text from another program onto the window. Pasted text is kept in a temporary file in `~/.cache/md-to-pdf/pasted/` (the 20 most recent are kept); to edit it, use **Menu → Open With Another App**, and the preview follows. Images with relative paths don't work in pasted text, since there is no reference folder; use absolute paths or URLs. If the clipboard holds a `.md` file (copied in the file manager), that file is opened.

| Shortcut | Action |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>O</kbd> | Open file |
| <kbd>Ctrl</kbd>+<kbd>V</kbd> | Paste Markdown text |
| <kbd>Ctrl</kbd>+<kbd>E</kbd> | Export PDF |
| <kbd>Ctrl</kbd>+<kbd>R</kbd> or <kbd>F5</kbd> | Reload (e.g. after replacing an image) |
| <kbd>F9</kbd> | Show/hide the options |
| <kbd>Ctrl</kbd>+<kbd>+</kbd> / <kbd>Ctrl</kbd>+<kbd>−</kbd> / <kbd>Ctrl</kbd>+mouse wheel | Zoom |
| <kbd>Ctrl</kbd>+<kbd>0</kbd> | Fit to width |
| <kbd>Ctrl</kbd>+<kbd>,</kbd> | Preferences |

### Command line

```sh
md-to-pdf notes.md                          # open in the window
md-to-pdf --export notes.md                 # writes notes.pdf next to it
md-to-pdf --export notes.md -o out.pdf      # choose the output file
md-to-pdf --export *.md                     # convert several at once
md-to-pdf --debug                           # log in ~/.cache/md-to-pdf/debug.log
```

Command-line export uses the same options chosen in the app (paper, margins, style…).

Preferences are stored in `~/.config/md-to-pdf/settings.json`.

## Updates

The app checks the latest GitHub release when it opens (this can be turned off in **Menu → Preferences**) and in **Menu → Check for updates**. When a new version exists, it shows what's new and offers **Update**: it downloads the package, verifies the size and SHA-256 reported by GitHub and installs it with `pkexec pacman -U`, which asks for your password in a system window. Then restart the app; the open file is reopened in the new version.

When running from source, the app only announces the new version and points to GitHub.

### Publishing a release

1. Bump `APP_VERSION` in `usr/share/md-to-pdf/core/__init__.py` (the PKGBUILD reads the version from there).
2. Build the package: `cd pkgbuild && makepkg -f`.
3. Create a GitHub release with the tag `v<version>` (e.g. `v1.0.1`), write the release notes in the description and attach `md-to-pdf-<version>-1-any.pkg.tar.zst`.

The release notes appear in the update dialog. To ship a packaging-only fix, bump `pkgrel` in the PKGBUILD: the updater compares `pkgrel` too.

## Translations

Texts are in English in the code; translations live in `po/`.

```sh
make update-po   # updates po/pt_BR.po with new texts from the code
make stats       # shows how many texts are translated
make             # compiles the .mo files to run without installing
```

To add a language: `msginit -i po/md-to-pdf.pot -l <code> -o po/<code>.po` and add the code to `po/LINGUAS`.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

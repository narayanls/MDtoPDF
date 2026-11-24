---
title: Demonstração do MDtoPDF
author: narayanls
lang: pt-BR
keywords: [markdown, pdf, exemplo]
---

# Demonstração do MDtoPDF

Este arquivo mostra o que o **MDtoPDF** sabe formatar. Abra-o no app e
exporte para ver o resultado — ou rode `md-to-pdf --export examples/demo.md`.

## Texto

Parágrafos com **negrito**, *itálico*, ***os dois***, ~~tachado~~, `código` e
[links](https://github.com/narayanls/MDtoPDF). Links internos também funcionam:
[ir para as tabelas](#tabelas). Teclas: <kbd>Ctrl</kbd> + <kbd>E</kbd>.
Notas de rodapé ficam no fim do documento.[^nota]

> Citações ficam com uma barra à esquerda.
> Podem ter várias linhas.

## Listas

1. Primeiro item
2. Segundo item
   - Sublista com dois espaços
   - Funciona como no GitHub
3. Terceiro item

- [x] Lista de tarefas concluída
- [ ] Tarefa pendente

Termo
: Definição do termo (lista de definição).

## Tabelas

| Recurso          | Suporte | Observação                   |
|:-----------------|:-------:|-----------------------------:|
| Tabelas          |   Sim   | Cabeçalho repete na página   |
| Realce de código |   Sim   | Via Pygments                 |
| Emojis           |   Sim   | Com a fonte Noto Color Emoji |

## Código

```python
def saudacao(nome: str) -> str:
    """Devolve uma saudação."""
    return f"Olá, {nome}!"  # comentário


print(saudacao("mundo"))
```

```bash
md-to-pdf --export relatorio.md -o relatorio.pdf
```

## Alertas

> [!NOTE]
> Alertas no estilo do GitHub viram caixas coloridas.

> [!WARNING]
> Imagens são procuradas a partir da pasta do arquivo `.md`.

\newpage

## Quebra de página

Esta seção começa numa página nova por causa do `\newpage` acima
(também vale `<!-- pagebreak -->`).

---

Fim da demonstração.

[^nota]: Esta é uma nota de rodapé.

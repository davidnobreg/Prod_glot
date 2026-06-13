# Prompt para Claude Code — Organizar a Pasta `docs/` do Projeto Glot

## Objetivo

Usar o Claude Code para organizar a pasta `docs/` do projeto **Glot**, deixando a documentação mais limpa, navegável e útil como memória técnica do projeto.

A pasta `docs/` está crescendo com muitos arquivos `.md`, alguns soltos na raiz e outros em pastas como:

```text
docs/
├── documentos/
├── frontend/
├── prompts/
├── API.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── CONVENTIONS.md
├── DATABASE.md
├── DEPLOY.md
├── GUIA_OBSIDIAN_DEV_VAULT.md
├── RELATORIO_TELA_CLIENTES.md
├── ROADMAP.md
└── SECURITY.md
```

A tarefa é organizar essa estrutura sem apagar nada e sem mexer no código do sistema.

---

## Regras Obrigatórias

### 1. Não apagar arquivos

Não delete nenhum arquivo.

Se algum arquivo parecer antigo, duplicado, rascunho ou fora de uso, mova para:

```text
docs/archive/
```

---

### 2. Trabalhar somente dentro da pasta `docs/`

Não alterar arquivos Python, HTML, CSS, JS, configurações Django, Docker, migrations ou qualquer outro arquivo fora de `docs/`.

Esta tarefa é exclusivamente de organização da documentação.

---

### 3. Não fazer commit automaticamente

Ao final, apenas executar:

```bash
git status
```

E mostrar o resultado.

Não fazer:

```bash
git add
git commit
git push
```

Sem autorização manual.

---

## Estrutura Desejada

Organizar a pasta `docs/` para ficar assim:

```text
docs/
├── README.md
├── INDEX.md
├── CLAUDE_CONTEXT.md
│
├── core/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── DEPLOY.md
│   ├── ROADMAP.md
│   └── SECURITY.md
│
├── processos/
│   ├── CONTRIBUTING.md
│   └── CONVENTIONS.md
│
├── documentos/
│
├── frontend/
│
├── prompts/
│
├── relatorios/
│   └── RELATORIO_TELA_CLIENTES.md
│
├── obsidian/
│   └── GUIA_OBSIDIAN_DEV_VAULT.md
│
└── archive/
```

---

## Pastas que Devem Existir

Criar estas pastas caso ainda não existam:

```bash
docs/core
docs/processos
docs/relatorios
docs/obsidian
docs/archive
```

Manter as pastas já existentes:

```bash
docs/documentos
docs/frontend
docs/prompts
```

---

## Classificação dos Arquivos

Mover os arquivos da raiz de `docs/` conforme a tabela abaixo.

| Arquivo atual | Destino |
|---|---|
| `API.md` | `docs/core/API.md` |
| `ARCHITECTURE.md` | `docs/core/ARCHITECTURE.md` |
| `DATABASE.md` | `docs/core/DATABASE.md` |
| `DEPLOY.md` | `docs/core/DEPLOY.md` |
| `ROADMAP.md` | `docs/core/ROADMAP.md` |
| `SECURITY.md` | `docs/core/SECURITY.md` |
| `CONTRIBUTING.md` | `docs/processos/CONTRIBUTING.md` |
| `CONVENTIONS.md` | `docs/processos/CONVENTIONS.md` |
| `RELATORIO_TELA_CLIENTES.md` | `docs/relatorios/RELATORIO_TELA_CLIENTES.md` |
| `GUIA_OBSIDIAN_DEV_VAULT.md` | `docs/obsidian/GUIA_OBSIDIAN_DEV_VAULT.md` |

---

## Arquivos Principais que Devem Ser Criados ou Atualizados

Criar ou atualizar estes arquivos:

```text
docs/README.md
docs/INDEX.md
docs/CLAUDE_CONTEXT.md
```

---

# Conteúdo Esperado dos Arquivos

## 1. `docs/README.md`

Criar ou atualizar com este conteúdo base:

```md
# Documentação do Projeto Glot

Esta pasta reúne a documentação técnica, funcional e operacional do projeto Glot.

## Estrutura

- `core/` — documentação principal do sistema, arquitetura, banco, deploy, API, roadmap e segurança.
- `processos/` — convenções, contribuição e padrões de trabalho.
- `documentos/` — documentação relacionada ao módulo de documentos, contratos, propostas e geração de arquivos.
- `frontend/` — documentação sobre telas, templates, Tailwind, componentes e experiência visual.
- `prompts/` — prompts usados com Claude Code, Codex, ChatGPT e outros agentes de IA.
- `relatorios/` — relatórios de auditoria, diagnóstico, análise e revisão.
- `obsidian/` — guias e integração com Obsidian/dev-vault.
- `archive/` — documentos antigos, rascunhos, duplicados ou materiais superados.

## Arquivos principais

- `INDEX.md` — índice navegável da documentação.
- `CLAUDE_CONTEXT.md` — ponto de entrada para agentes de IA.

## Regra principal

Não criar arquivos Markdown soltos na raiz de `docs/`.

A raiz deve conter apenas:

- `README.md`
- `INDEX.md`
- `CLAUDE_CONTEXT.md`

Todo novo arquivo `.md` deve ser criado dentro da pasta correta.
```

---

## 2. `docs/INDEX.md`

Criar ou atualizar um índice com links reais para os arquivos existentes.

Modelo inicial:

```md
# Índice da Documentação — Glot

## Arquivos Principais

- [README](README.md)
- [Contexto para Claude Code](CLAUDE_CONTEXT.md)

## Core

- [API](core/API.md)
- [Arquitetura](core/ARCHITECTURE.md)
- [Banco de Dados](core/DATABASE.md)
- [Deploy](core/DEPLOY.md)
- [Roadmap](core/ROADMAP.md)
- [Segurança](core/SECURITY.md)

## Processos

- [Contribuição](processos/CONTRIBUTING.md)
- [Convenções](processos/CONVENTIONS.md)

## Documentos

Listar aqui os arquivos existentes dentro de `docs/documentos/`.

## Frontend

Listar aqui os arquivos existentes dentro de `docs/frontend/`.

## Prompts

Listar aqui os arquivos existentes dentro de `docs/prompts/`.

## Relatórios

- [Relatório Tela Clientes](relatorios/RELATORIO_TELA_CLIENTES.md)

## Obsidian

- [Guia Obsidian Dev Vault](obsidian/GUIA_OBSIDIAN_DEV_VAULT.md)

## Arquivo Morto

Arquivos antigos, rascunhos ou materiais superados ficam em `archive/`.
```

Importante:

- Não inventar links para arquivos que não existem.
- Se houver arquivos dentro de `documentos/`, `frontend/` ou `prompts/`, listar no índice.
- Se algum link ficar quebrado, registrar no relatório final.

---

## 3. `docs/CLAUDE_CONTEXT.md`

Criar ou atualizar com este conteúdo:

```md
# Contexto para Claude Code — Projeto Glot

Este arquivo é o ponto de entrada para o Claude Code entender a documentação do projeto Glot.

## Antes de iniciar qualquer tarefa

Leia primeiro:

1. `docs/INDEX.md`
2. `docs/core/ARCHITECTURE.md`
3. `docs/core/DATABASE.md`
4. `docs/core/ROADMAP.md`
5. `docs/processos/CONVENTIONS.md`

## Organização da pasta `docs/`

A documentação está separada por função:

- `core/` — documentação principal do sistema.
- `processos/` — padrões, contribuição e convenções.
- `documentos/` — contratos, propostas, distratos e editor de documentos.
- `frontend/` — telas, templates, Tailwind e componentes visuais.
- `prompts/` — prompts para agentes de IA.
- `relatorios/` — relatórios de auditoria e diagnóstico.
- `obsidian/` — guias de integração com Obsidian/dev-vault.
- `archive/` — documentos antigos ou superados.

## Regras para novos arquivos Markdown

- Não criar arquivos `.md` soltos na raiz de `docs/`.
- Prompts devem ir para `docs/prompts/`.
- Relatórios devem ir para `docs/relatorios/`.
- Documentação de frontend deve ir para `docs/frontend/`.
- Documentação sobre contratos, propostas e documentos deve ir para `docs/documentos/`.
- Documentação central do sistema deve ir para `docs/core/`.
- Convenções e processos devem ir para `docs/processos/`.
- Conteúdo antigo deve ir para `docs/archive/`.

## Regras de segurança

- Não apagar documentação sem autorização.
- Não mover arquivos para fora de `docs/`.
- Não alterar código do sistema nesta tarefa.
- Não fazer commit sem autorização.
- Sempre mostrar o `git status` ao final.

## Objetivo

Manter a pasta `docs/` organizada para servir como memória técnica do projeto e facilitar o trabalho com Claude Code, Codex e ChatGPT.
```

---

# Relatório Final

Criar o arquivo:

```text
docs/relatorios/organizacao_docs_glot.md
```

Com o seguinte conteúdo:

```md
# Relatório — Organização da Pasta docs do Glot

## Objetivo

Organizar a pasta `docs/` do projeto Glot.

## Estrutura criada

Listar as pastas criadas.

## Arquivos movidos

Listar os arquivos movidos, no formato:

- `docs/API.md` → `docs/core/API.md`

## Arquivos criados

Listar os arquivos criados:

- `docs/README.md`
- `docs/INDEX.md`
- `docs/CLAUDE_CONTEXT.md`
- `docs/relatorios/organizacao_docs_glot.md`

## Arquivos arquivados

Listar arquivos movidos para `archive/`, caso existam.

## Links revisados

Informar se os links internos foram revisados.

## Pendências

Listar qualquer dúvida ou arquivo que precisa de decisão manual.

## Git status

Colar o resultado do comando:

```bash
git status
```
```

---

# Validações Obrigatórias

Depois de organizar, executar:

```bash
git status
```

E também verificar a árvore da pasta `docs/`.

No Windows PowerShell, pode usar:

```powershell
tree docs /F
```

Ou, se estiver no Git Bash/Linux:

```bash
find docs -maxdepth 3 -type f | sort
```

---

# Comando para Executar no Claude Code

Depois de salvar este arquivo, execute o Claude Code e envie:

```text
Leia e execute o arquivo docs/prompts/prompt_organizar_docs_glot.md.

Regras:
- Não apague nenhum arquivo.
- Não altere código do sistema.
- Trabalhe somente dentro da pasta docs.
- Organize os arquivos conforme o plano.
- Crie ou atualize README.md, INDEX.md e CLAUDE_CONTEXT.md.
- Crie o relatório final em docs/relatorios/organizacao_docs_glot.md.
- Ao final, mostre o git status.
```

---

# Resultado Esperado

Ao final, a pasta `docs/` deve estar limpa, com os arquivos principais na raiz e o restante organizado por função.

A raiz de `docs/` deve conter apenas:

```text
README.md
INDEX.md
CLAUDE_CONTEXT.md
documentos/
frontend/
prompts/
core/
processos/
relatorios/
obsidian/
archive/
```

Nenhum arquivo Markdown técnico deve ficar solto na raiz, exceto os três arquivos principais:

```text
README.md
INDEX.md
CLAUDE_CONTEXT.md
```

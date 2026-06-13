# Como usar o dev-vault

## Filosofia
O vault é sua memória externa + memória do Claude Code.
Tudo que você não quer explicar de novo — decisões, bugs, padrões — fica aqui.
O Claude Code lê automaticamente via CLAUDE.md.

---

## Para que serve cada pasta

### 00-inbox
**Dump rápido.** Anotou algo rápido, ideia, link, trecho de código?
Joga aqui primeiro. Organiza depois.
> Exemplo: "testar WeasyPrint com fonte personalizada"

### 01-projetos
**Um arquivo por projeto** com contexto permanente.
O Claude Code lê isso para entender o projeto sem você explicar do zero.
> Exemplo: `GLOT.md`, `ImobCloud.md`
> Conteúdo: stack, arquitetura, decisões importantes, o que está em andamento

### 02-decisoes
**Decisões de arquitetura que não podem ser revertidas sem motivo.**
Formato: problema → opções consideradas → decisão → motivo.
> Exemplo: "Por que usamos django-tenants em vez de row-level isolation"
> Exemplo: "Por que o deploy é imagem imutável e não git pull"

### 03-bugs
**Bugs que custaram tempo para resolver.**
Formato: sintoma → causa raiz → solução.
> Exemplo: o erro 500 do PDF (media serving no nginx)
> Exemplo: `no suitable node (unsupported platform)` no Swarm

### 04-snippets
**Código que você reutiliza.**
> Exemplo: configuração do Celery worker
> Exemplo: bloco nginx para media
> Exemplo: comando de deploy manual via Portainer

### 05-aprendizados
**Conceitos que você entendeu e quer fixar.**
Não é tutorial — é o que fez sentido pra você.
> Exemplo: "Como o Docker Swarm resolve plataforma de imagem"
> Exemplo: "Por que COPY requirements antes de COPY . no Dockerfile"

### 06-referencias
**Links e documentações que você sempre volta.**
> Exemplo: API do Portainer, docs do django-tenants, Evolution API

### 07-diario
**Log de sessões de desenvolvimento.**
Um arquivo por dia. O que foi feito, o que ficou pendente.
> Formato: `2026-06-12.md`

### Claude Code
**Instruções e contexto para o Claude Code.**
CLAUDE.md global e por projeto ficam aqui.
Não edite manualmente — o Claude Code atualiza quando necessário.

---

## Fluxo recomendado

### Durante o desenvolvimento
1. Bug difícil resolvido → anota em `03-bugs`
2. Decisão importante tomada → anota em `02-decisoes`
3. Aprendeu algo novo → anota em `05-aprendizados`
4. Código útil → anota em `04-snippets`

### No final de cada sessão (5 minutos)
Pede para o Claude Code:
```
Gera o diário de hoje para o Obsidian baseado no que fizemos
```
Ele gera um arquivo `07-diario/2026-XX-XX.md` com resumo da sessão,
decisões tomadas e pendências.

### Quando começar uma nova sessão
O Claude Code lê o vault automaticamente e já sabe o contexto.
Você não precisa explicar o que foi feito antes.

---

## Sobre a pasta "docs" bagunçada
Você mencionou que está jogando tudo em docs.
Peça para o Claude Code organizar:
```
Organiza os arquivos da pasta docs do vault Obsidian
nas pastas corretas (03-bugs, 02-decisoes, etc)
baseado no conteúdo de cada arquivo
```

---

## Arquivos que o Claude Code gera automaticamente

| Arquivo | Pasta | Quando |
|---|---|---|
| Diário da sessão | `07-diario/` | Fim de cada sessão |
| Decisões de arquitetura | `02-decisoes/` | Quando uma decisão importante é tomada |
| Bug resolvido | `03-bugs/` | Quando um bug complexo é fechado |
| Contexto do projeto | `01-projetos/` | Quando o contexto muda significativamente |

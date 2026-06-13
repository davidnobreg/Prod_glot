# GLOT — Migração Tailwind — Módulo Usuários

## Contexto

O módulo de usuários tem telas em mix de AdminLTE e Tailwind. O objetivo é
padronizar **todas** as telas para Tailwind, seguindo o padrão visual já
adotado nas telas recentes do GLOT (empreendimentos, grupos, etc.).

---

## Passo 1 — Levantamento (fazer antes de qualquer alteração)

Listar todos os templates do módulo usuários:

```bash
find . -path "*/usuarios/templates*" -name "*.html" | sort
```

Para cada template encontrado, identificar:
- Nome do arquivo
- Está em AdminLTE ou Tailwind (verificar se usa `class="card"` AdminLTE vs `class="bg-white rounded-lg"` Tailwind)
- Função da tela

Reportar o levantamento antes de continuar.

---

## Passo 2 — Migrar cada tela para Tailwind

Migrar todas as telas encontradas. Para cada uma seguir o padrão:

### Padrão visual Tailwind do GLOT

Seguir exatamente o mesmo padrão das telas já migradas no projeto
(empreendimentos, grupos). Verificar um template Tailwind existente como
referência antes de começar.

Elementos padrão:
- Container: `max-w-7xl mx-auto px-4 py-6`
- Cards: `bg-white rounded-lg shadow-sm border border-gray-200`
- Títulos de seção: `text-lg font-semibold text-gray-800`
- Botão primário: padrão já usado no projeto (verificar)
- Botão perigo: padrão já usado no projeto (verificar)
- Tabelas: `min-w-full divide-y divide-gray-200` com header `bg-gray-50`
- Badges de status: coloridos conforme padrão existente
- Mensagens Django (`messages`): alertas com ícone e botão fechar

---

## Telas a migrar

### 1. Lista de usuários

Elementos:
- Cabeçalho com título "Usuários" + botão "Novo Usuário"
- Campo de busca por nome/email
- Filtro por grupo
- Tabela: Avatar/Inicial, Nome, Email, Grupos, Último acesso, Status (ativo/inativo), Ações
- Ações por linha: Editar, Gerenciar Grupos
- Paginação

### 2. Detalhe do usuário

Elementos:
- Card superior: avatar com inicial, nome completo, email, grupos atuais (badges), status
- Botões: Editar, Gerenciar Grupos
- Seção de vendas do corretor (já implementada — não remover, apenas estilizar se necessário)

### 3. Criar usuário / Editar usuário

Elementos:
- Formulário em card: Nome, Sobrenome, Email, Username, Senha, Grupos, Ativo
- Botões: Salvar, Cancelar

### 4. Associar grupos

Elementos (já implementado na etapa anterior — verificar se precisa de ajuste visual):
- Título com nome do usuário
- Lista de checkboxes com contagem de usuários por grupo
- Botões: Salvar, Cancelar

### 5. Telas de grupos (lista_grupos, form_grupo)

Verificar se já estão em Tailwind. Se não estiverem, migrar também.

---

## Regras

- Não alterar nenhuma view, URL ou lógica Python — só templates
- Não remover a seção de vendas do corretor no detalhe do usuário
- Preservar todos os `{% url %}`, `{% csrf_token %}`, `{% if %}` e lógica de template existente
- Manter `{% extends 'base.html' %}` e `{% block %}` corretos
- Verificar um template Tailwind existente do projeto como referência visual antes de começar

---

## Como testar

1. Acessar `/usuarios/` — lista renderiza corretamente em Tailwind
2. Clicar em um usuário — detalhe abre sem erros
3. Editar usuário — formulário salva corretamente
4. Gerenciar grupos de um usuário — checkboxes funcionam
5. `python manage.py check` → 0 erros

---

## Arquivos esperados ao final

Relatório com:
- Lista de templates encontrados no levantamento
- Quais já estavam em Tailwind (apenas ajustes se necessário)
- Quais foram migrados do AdminLTE
- Resultado do `python manage.py check`

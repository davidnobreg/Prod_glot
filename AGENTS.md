# AGENTS.md

## Visão Geral

Glot é um sistema monolítico desenvolvido em Django com arquitetura modular baseada em apps.

O sistema possui módulos administrativos, vendas, clientes, empreendimentos, documentos, cobrança, mensagens e dashboard.

A aplicação utiliza:

- Django
- Django Templates
- Bootstrap/AdminLTE
- Jazzmin
- CKEditor
- Django REST Framework
- SQLite/PostgreSQL (inferido)
- Estrutura tradicional MVC do Django

---

# Estrutura Principal

```txt
accounts/
base/
clientes/
cobranca/
configuration/
core/
dashboard/
documentos/
empreendimentos/
mensagem/
vendas/
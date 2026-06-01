
---

# DATABASE.md

```md
# DATABASE.md

# Banco de Dados

---

# Regras Gerais

- utilizar ORM Django
- evitar SQL bruto
- preservar compatibilidade

---

# Relacionamentos

O sistema possui múltiplos módulos integrados:

- clientes
- vendas
- empreendimentos
- documentos

---

# Regras

## Nunca

- apagar migrations antigas
- recriar tabelas automaticamente

---

# Migrations

Sempre executar:

```bash
python manage.py makemigrations
python manage.py migrate
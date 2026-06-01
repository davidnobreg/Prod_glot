
---

# SECURITY.md

```md
# SECURITY.md

# Segurança

---

# Nunca

- expor SECRET_KEY
- salvar senhas em texto puro
- desabilitar CSRF
- confiar em input do usuário

---

# Sempre

- validar inputs
- usar ORM Django
- revisar permissões
- validar uploads

---

# Uploads

Validar:

- extensão
- tamanho
- tipo MIME

---

# SQL Injection

Evitar:

```python
cursor.execute(f"SELECT * FROM {user_input}")
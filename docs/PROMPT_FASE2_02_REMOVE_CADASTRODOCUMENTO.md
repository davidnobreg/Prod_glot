# Fix — Remover CadastroDocumento legado

## Contexto
O model `CadastroDocumento` ainda existe em `documentos/models.py` (linhas 10–47).
É um model legado substituído por `ModeloDocumento` + `EmpreendimentoDocumento`.
A migration `0010_migra_cadastro_para_modelo.py` já migrou os dados.

## Antes de remover qualquer coisa — auditoria completa

Buscar TODAS as referências a `CadastroDocumento` no projeto:

```bash
grep -rn "CadastroDocumento" --include="*.py" .
grep -rn "CadastroDocumento" --include="*.html" .
grep -rn "cadastro_documento\|cadastrodocumento" --include="*.py" . -i
```

Se encontrar qualquer referência fora de:
- `documentos/migrations/` (histórico — esperado, não tocar)
- `documentos/models.py` (o próprio model — será removido)

**PARAR e reportar antes de continuar.**

---

## Remoção (só executar se a auditoria não encontrar referências ativas)

### 1. Remover de `documentos/models.py`
- Remover a classe `CadastroDocumento` completa
- Remover imports que eram usados exclusivamente por ela (verificar)
- Não tocar em nenhum outro model

### 2. Gerar migration de limpeza
```bash
python manage.py makemigrations documentos --name="remove_cadastrodocumento"
```

Confirmar que a migration gerada é apenas `DeleteModel('CadastroDocumento')`.
Se gerar qualquer outra alteração além disso, reportar antes de continuar.

### 3. Verificar admin
```bash
grep -n "CadastroDocumento" documentos/admin.py
```
Se existir registro no admin, remover também.

---

## O que NÃO alterar
- Migrations históricas (`0001` a `0010`) — não tocar
- Nenhum outro model
- Nenhuma view

---

## Entregáveis
1. Output do grep de auditoria confirmando zero referências ativas
2. Diff de `documentos/models.py` com a classe removida
3. Migration gerada (`remove_cadastrodocumento`)
4. Diff de `documentos/admin.py` se necessário

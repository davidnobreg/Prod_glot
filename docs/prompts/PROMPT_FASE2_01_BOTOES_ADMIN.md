# Fix — Ocultar botões Finalizar/Cancelar para não-admin no template

## Contexto
Em `documento_detalhe.html`, os botões "Finalizar" e "Cancelar" aparecem
para qualquer usuário autenticado. A proteção existe na view, mas o template
não filtra por role — usuários não-admin veem botões que retornam erro ao clicar.

## Leia antes de alterar
```
documentos/templates/documentos/documento_detalhe.html
```

Identifique exatamente como o role do usuário é verificado nos outros templates
do projeto (ex: `analisa.html`, `reservado_detalhe.html`) para usar o mesmo padrão.
Pode ser `request.user.tipo_usuario`, `request.user.role`, ou via templatetag customizada.

---

## Correção

Envolver os botões "Finalizar" e "Cancelar" com a condição de administrador,
usando o mesmo padrão já adotado no projeto.

Exemplo (ajustar conforme o padrão real encontrado):
```html
{% if request.user.tipo_usuario == 'ADMINISTRADOR' %}
  <!-- botão Finalizar -->
  <!-- botão Cancelar -->
{% endif %}
```

Não alterar a lógica das views — a proteção na view permanece como está.
Não alterar nenhum outro template.

---

## Validação
1. Logar como Corretor
2. Acessar o detalhe de um `DocumentoGerado` do tipo `proposta`
3. Botões "Finalizar" e "Cancelar" não devem aparecer
4. Logar como Administrador — botões devem aparecer normalmente

# Inventario static antes do Tailwind no GLOT

## Confirmacao principal

No fluxo atual do projeto, os arquivos CSS e JS editaveis ficam em:

```txt
base/static/
```

Depois das alteracoes, o comando:

```bash
python manage.py collectstatic
```

copia/coleta esses arquivos para:

```txt
static/
```

Portanto:

- `base/static/` e a origem correta para editar CSS/JS do projeto.
- `static/` e o destino de `collectstatic`, nao deve ser tratado como fonte principal de edicao.

## Configuracao Django encontrada

Arquivo:

```txt
core/settings.py
```

Configuracao:

```python
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
```

Tambem existe:

```python
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'base/static')]
```

Esse `STATICFILES_DIRS` esta comentado.

Mesmo assim, como o app `base` esta em `INSTALLED_APPS`, o Django encontra os arquivos dentro de:

```txt
base/static/
```

## Resultado confirmado com findstatic

Comando usado:

```bash
python manage.py findstatic css/style.css js/geral.js js/cliente.js js/empreendimento.js js/jquery.mask.min.js --verbosity 2
```

Resultado confirmado:

```txt
css/style.css
-> base/static/css/style.css

js/geral.js
-> base/static/js/geral.js

js/cliente.js
-> base/static/js/cliente.js

js/empreendimento.js
-> base/static/js/empreendimento.js

js/jquery.mask.min.js
-> base/static/js/jquery.mask.min.js
```

## CSS carregado atualmente

Arquivo:

```txt
base/templates/base.html
```

Trecho:

```django
<link
    rel="stylesheet"
    href="{% static 'css/style.css' %}"
>
```

Como `findstatic` resolve `css/style.css` para `base/static/css/style.css`, o CSS principal real e:

```txt
base/static/css/style.css
```

## JS global carregado atualmente

Arquivo:

```txt
base/templates/base.html
```

Arquivos locais carregados:

```django
{% static 'js/jquery.mask.min.js' %}
{% static 'js/empreendimento.js' %}
{% static 'js/geral.js' %}
{% static 'js/cliente.js' %}
{% static 'js/cep.js' %}
{% static 'js/conjuge.js' %}
{% static 'js/telefone.js' %}
```

Todos resolvem preferencialmente a partir de:

```txt
base/static/js/
```

## Dependencias globais carregadas por CDN

O layout base carrega:

- Bootstrap CSS `5.3.3`
- Bootstrap Icons
- Font Awesome
- Select2 CSS/JS
- Flatpickr CSS/JS
- Flatpickr locale `pt`
- jQuery `3.7.1`
- Bootstrap bundle JS `5.3.3`
- html2canvas

## Arquivos duplicados ou suspeitos

Existem arquivos parecidos em:

```txt
base/static/css/style.css
static/css/style.css
base/static/css/style_new.css
```

Interpretacao:

- `base/static/css/style.css`: arquivo principal editavel.
- `static/css/style.css`: provavel saida/coleta do `collectstatic` ou copia antiga.
- `base/static/css/style_new.css`: arquivo experimental/nao carregado pelo `base.html`.

Tambem existem duplicatas de JS:

```txt
base/static/js/
static/js/
```

Interpretacao:

- editar em `base/static/js/`.
- nao editar diretamente em `static/js/`, salvo manutencao excepcional.

## Risco para Tailwind

O maior risco e adicionar Tailwind de forma global e com reset/preflight ativo, porque o projeto depende fortemente de classes e comportamento Bootstrap:

- `btn`
- `form-control`
- `form-select`
- `table`
- `modal`
- `alert`
- `navbar`
- `dropdown`
- `card`
- `row`
- `col-*`

Tambem ha JS dependente de Bootstrap, jQuery, Select2 e Flatpickr.

## Recomendacao segura para instalar Tailwind

Instalar Tailwind em paralelo, sem substituir Bootstrap.

Recomendacao objetiva:

1. Manter `base/static/css/style.css` como esta.
2. Criar um CSS separado para Tailwind, por exemplo:

```txt
base/static/css/tailwind.css
```

3. Usar prefixo no Tailwind:

```js
prefix: 'tw-'
```

4. Desativar o preflight inicialmente:

```js
corePlugins: {
    preflight: false,
}
```

5. Nao carregar Tailwind globalmente no primeiro passo.
6. Carregar Tailwind somente em uma tela piloto.
7. Evitar mexer em templates com modais, Select2, Flatpickr e formularios complexos na primeira etapa.

## Primeira tela piloto recomendada

Tela recomendada:

```txt
dashboard/templates/dash.html
```

Motivo:

- Estende `base.html`.
- Menor risco de quebrar fluxo critico.
- Boa para validar Tailwind em paralelo.

Segunda opcao, ainda mais isolada:

```txt
base/templates/not_found.html
```

## Conclusao

Para o GLOT, o caminho correto antes do Tailwind e:

```txt
editar em base/static/
rodar python manage.py collectstatic
servir a partir de static/
```

Na instalacao inicial do Tailwind, nao sobrescrever `style.css`, nao remover Bootstrap e nao ativar reset global.

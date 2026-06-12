from django.template import Template, Context
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from .models import CadastroDocumento, ModeloDocumento
from .services import (
    construir_contexto_venda,
    montar_contexto_venda,
    renderizar_variaveis,
)
from clientes.models import ClienteTelefone
from vendas.models import RegisterVenda
from rolepermissions.decorators import has_permission_decorator


# =====================================================
# HELPERS
# =====================================================

def _get_venda(venda_uuid, por_lote=False):
    qs = RegisterVenda.objects.select_related(
        'cliente',
        'lote',
        'lote__quadra',
        'lote__quadra__empr',
        'user',
    )
    campo = 'lote__uuid' if por_lote else 'uuid'
    return get_object_or_404(qs, **{campo: venda_uuid})


def _renderizar_documento(tipo, contexto):
    documento = (
        CadastroDocumento.objects
        .filter(tipo=tipo, ativo=True)
        .order_by('-versao')
        .first()
    )
    if not documento:
        raise Http404(f"Documento '{tipo}' não encontrado")
    return Template(documento.texto).render(Context(contexto))


# =====================================================
# VIEWS
# =====================================================

@has_permission_decorator('proposta')
def proposta(request, venda_uuid):
    """Proposta via novo módulo de documentos (ModeloDocumento + variáveis globais).

    Busca o modelo de proposta padrão do empreendimento (ou o global como
    fallback), renderiza com o contexto da venda e exibe na tela de preview
    existente. Sem modelo no novo módulo, cai na view legada.
    """
    venda = _get_venda(venda_uuid)
    empreendimento = venda.lote.quadra.empr
    modelo = ModeloDocumento.objects.padrao_para(empreendimento, 'proposta')
    if not modelo:
        return proposta_legado(request, venda_uuid)
    contexto = montar_contexto_venda(venda, request.user)
    html_final = renderizar_variaveis(modelo.conteudo_html, contexto)
    return render(request, 'proposta.html', {
        'html_final': html_final,
        'venda': venda,
    })


@has_permission_decorator('proposta')
def proposta_legado(request, venda_uuid):
    venda = _get_venda(venda_uuid)
    contato_cliente = ClienteTelefone.objects.filter(cliente=venda.cliente).first()
    contexto = construir_contexto_venda(venda, contato_cliente)
    html_final = _renderizar_documento('proposta', contexto)
    return render(request, 'proposta.html', {
        'html_final': html_final,
        'venda': venda,
    })

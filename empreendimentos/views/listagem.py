import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone

from documentos.models import ModeloDocumento, EmpreendimentoDocumento

from ..forms import EmpreendimentoUpdateForm
from ..models import Empreendimento, Lote
from accounts.models import User, UsuarioEmpreendimento


@has_permission_decorator('listaEmpreendimento')
def listaEmpreendimento(request):
    # Filtrando os empreendimentos que estão inativos e vinculados ao usuário logado
    empreendimentos_ids = UsuarioEmpreendimento.objects.filter(usuario=request.user, ativo=True).values_list(
        'empreendimento_id',
        flat=True)
    empreendimentos = Empreendimento.objects.filter(id__in=empreendimentos_ids, is_ativo=True)

    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos.html', context)


@has_permission_decorator('alterarEmpreendimento')
def alteraEmpreendimento(request, uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=uuid)

    # =========================
    # GET
    # =========================
    if request.method == 'GET':
        form = EmpreendimentoUpdateForm(instance=empreendimento)
        return render(request, 'update_empreendimento.html', {
            'form': form,
            'empreendimento': empreendimento
        })

    # =========================
    # POST
    # =========================
    form = EmpreendimentoUpdateForm(request.POST, request.FILES, instance=empreendimento)

    if not form.is_valid():
        messages.error(request, "Verifique os campos obrigatórios.")
        return render(request, 'update_empreendimento.html', {
            'form': form,
            'empreendimento': empreendimento
        })

    try:
        with transaction.atomic():

            obj = form.save(commit=False)

            # =========================
            # NORMALIZAR CNPJ (somente números)
            # =========================
            obj.cnpj = re.sub(r'\D', '', obj.cnpj)

            if len(obj.cnpj) != 14:
                raise ValidationError("CNPJ deve conter 14 números.")

            obj.full_clean()
            obj.save()

            messages.success(request, "Empreendimento atualizado com sucesso!")
            return redirect('lista-empreendimento-tabela')

    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))

    except Exception as e:
        messages.error(request, f"Erro ao atualizar empreendimento: {e}")

    return render(request, 'update_empreendimento.html', {
        'form': form,
        'empreendimento': empreendimento
    })



@has_permission_decorator('deletarEmpreendimento')
@require_POST
def deleteEmpreendimento(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    empreendimento.is_ativo = False
    empreendimento.save()
    return redirect('lista-empreendimento-tabela')


@has_permission_decorator('listaEmpreendimentoTabela')
def listaEmpreendimentoTabela(request):
    # Buscar empreendimentos que estão ativos
    empreendimentos = Empreendimento.objects.filter(is_ativo=True)

    get_empreendimento = request.GET.get('empreendimento')

    if get_empreendimento:
        empreendimentos = Empreendimento.objects.filter(nome=get_empreendimento)

    # Preparando os dados para exibição
    empreendimento_info = []

    for empreendimento in empreendimentos:
        # Lotes de cada empreendimento
        lotes = Lote.objects.filter(quadra__empr=empreendimento)

        total = lotes.count()
        livre = lotes.filter(situacao='DISPONIVEL').count()
        reservas = lotes.filter(situacao='RESERVADO').count()
        vendidos = lotes.filter(situacao='VENDIDO').count()
        outras = lotes.filter(
            Q(situacao='EM_RESERVA') |
            Q(situacao='CONSTRUTORA') |
            Q(situacao='INDISPONIVEL')
        ).count()

        # Adicionando as informações do empreendimento na lista
        empreendimento_info.append({
            'uuid': empreendimento.uuid,
            'nome': empreendimento.nome,
            'tempo_reserva': empreendimento.tempo_reserva,
            'quantidade_parcela': empreendimento.quantidade_parcela,
            'total': total,
            'livre': livre,
            'reservas': reservas,
            'vendidos': vendidos,
            'outras': outras,
        })

    context = {
        #'formArquivo': formArquivo,
        'empreendimentos': empreendimento_info
        #'arquivoempreendimento': arquivoempreendimento
    }
    return render(request, 'lista-empreendimentos-tabela.html', context)


def detalheEmpreendimento(request, uuid):
    template_name = 'detalhes-do-empreendimento.html'

    empreendimento = get_object_or_404(Empreendimento, uuid=uuid)

    # =========================
    # Paginação de usuários disponíveis
    # =========================
    ids_corretores = UsuarioEmpreendimento.objects.filter(
        empreendimento=empreendimento,
        ativo=True
    ).values_list('usuario_id', flat=True)

    usuarios_qs = User.objects.exclude(
        id__in=ids_corretores
    ).order_by('first_name', 'email')

    paginator_usuarios = Paginator(usuarios_qs, 5)
    page_usuarios = request.GET.get('page_usuarios', 1)
    usuarios = paginator_usuarios.get_page(page_usuarios)

    # =========================
    # Paginação de corretores vinculados
    # =========================
    corretores_qs = UsuarioEmpreendimento.objects.filter(
        empreendimento=empreendimento,
        ativo=True
    ).select_related('usuario').order_by(
        'usuario__first_name',
        'usuario__email'
    )

    paginator_corretores = Paginator(corretores_qs, 5)
    page_corretores = request.GET.get('page_corretores', 1)
    corretores = paginator_corretores.get_page(page_corretores)

    # =========================
    # Empreendimentos
    # =========================
    empreendimentos = Empreendimento.objects.all()

    # =========================
    # Estatísticas dos lotes
    # =========================
    lotes = Lote.objects.filter(quadra__empr=empreendimento)

    total = lotes.count()
    livre = lotes.filter(situacao='DISPONIVEL').count()
    reserva = lotes.filter(situacao='RESERVADO').count()
    vendido = lotes.filter(situacao='VENDIDO').count()
    outros = lotes.filter(
        Q(situacao='CONSTRUTORA') |
        Q(situacao='EM_RESERVA') |
        Q(situacao='INDISPONIVEL')
    ).count()

    # =========================
    # Modelos de documento vinculados
    # =========================
    modelos_vinculados = EmpreendimentoDocumento.objects.filter(
        empreendimento=empreendimento
    ).select_related('modelo').order_by(
        'modelo__tipo',
        'ordem'
    )

    ids_vinculados = modelos_vinculados.values_list('modelo_id', flat=True)

    modelos_disponiveis = ModeloDocumento.objects.filter(
        ativo=True
    ).exclude(
        id__in=ids_vinculados
    )

    context = {
        'empreendimento': empreendimento,
        'empreendimentos': empreendimentos,
        'usuarios': usuarios,
        'corretores': corretores,
        'total': total,
        'livre': livre,
        'reserva': reserva,
        'vendido': vendido,
        'outros': outros,
        'modelos_vinculados': modelos_vinculados,
        'modelos_disponiveis': modelos_disponiveis,
    }

    return render(request, template_name, context)


def relatorioFinanceiro(request, uuid):
    template_name = 'relatorio-financeiro.html'

    empreendimento = get_object_or_404(Empreendimento, uuid=uuid)

    lotes = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO') | Q(situacao='VENDIDO'))
    lotes_disponiveis = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')
    )
    lotes_vendidos = Lote.objects.filter(quadra__empr_id=empreendimento.id, situacao='VENDIDO')

    lotes_indisponivel = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='CONSTRUTORA') | Q(situacao='INDISPONIVEL')
    )

    quantidade_lotes = Lote.objects.filter(quadra__empr_id=empreendimento.id).count()
    quantidade_lotes_disponivel = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')).count()
    quantidade_lotes_vendidos = Lote.objects.filter(quadra__empr_id=empreendimento.id, situacao='VENDIDO').count()

    quantidade_lotes_indisponivel = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(
        Q(situacao='CONSTRUTORA') | Q(situacao='INDISPONIVEL')).count()

    data_atual = timezone.now()

    valor_total = 0

    for lote in lotes:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total += valor_lote

    parcelas_total = valor_total / empreendimento.quantidade_parcela

    # Formatar o valor total para moeda brasileira
    valor_total_formatado = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    parcelas_total_formatado = f"R$ {parcelas_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    valor_total_disponivel = 0

    for lote in lotes_disponiveis:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total_disponivel += valor_lote

    parcelas_total_disponivel = valor_total_disponivel / empreendimento.quantidade_parcela

    valor_total_disponivel_formatado = f"R$ {valor_total_disponivel:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", ".")

    parcelas_total_disponivel_formatado = f"R$ {parcelas_total_disponivel :,.2f}".replace(",", "X").replace(".",
                                                                                                            ",").replace(
        "X", ".")

    valor_total_vendidos = 0

    for lote in lotes_vendidos:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total_vendidos += valor_lote

    parcelas_total_vendidos = valor_total_vendidos / empreendimento.quantidade_parcela

    valor_total_vendidos_formatado = f"R$ {valor_total_vendidos:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", ".")

    parcelas_total_vendidos_formatado = f"R$ {parcelas_total_vendidos :,.2f}".replace(",", "X").replace(".",
                                                                                                        ",").replace(
        "X", ".")

    #LOTES INDISPONIVEL

    valor_total_indisponivel = 0

    for lote in lotes_indisponivel:
        try:
            area = float(lote.area)
            valor_metro = float(lote.valor_metro_quadrado)
            valor_lote = area * valor_metro
        except (TypeError, ValueError, AttributeError):
            valor_lote = 0

        valor_total_indisponivel += valor_lote

    parcelas_total_indisponivel = valor_total_indisponivel / empreendimento.quantidade_parcela

    valor_total_indisponivel_formatado = f"R$ {valor_total_indisponivel:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", ".")

    parcelas_total_indisponivel_formatado = f"R$ {parcelas_total_indisponivel :,.2f}".replace(",", "X").replace(".",
                                                                                                        ",").replace(
        "X", ".")

    # Exemplo de retorno ou envio para o template

    context = {
        'data_atual': data_atual,
        'empreendimento': empreendimento,
        'quantidade_lotes': quantidade_lotes,
        'quantidade_lotes_disponivel': quantidade_lotes_disponivel,
        'quantidade_lotes_vendidos': quantidade_lotes_vendidos,
        'quantidade_lotes_indisponivel': quantidade_lotes_indisponivel,
        'valor_total_formatado': valor_total_formatado,
        'parcelas_total_formatado': parcelas_total_formatado,
        'valor_total_disponivel_formatado': valor_total_disponivel_formatado,
        'parcelas_total_disponivel_formatado': parcelas_total_disponivel_formatado,
        'valor_total_vendidos_formatado': valor_total_vendidos_formatado,
        'parcelas_total_vendidos_formatado': parcelas_total_vendidos_formatado,
        'valor_total_indisponivel_formatado': valor_total_indisponivel_formatado,
        'parcelas_total_indisponivel_formatado': parcelas_total_indisponivel_formatado
    }

    return render(request, template_name, context)

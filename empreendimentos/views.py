import json
import os
import re
from datetime import date
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from rolepermissions.decorators import has_permission_decorator

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views import View

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

from documentos.models import ModeloDocumento, EmpreendimentoDocumento

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


from tornado.http1connection import parse_int

from .forms import (EmpreendimentoForm, ArquivoForm, LoteForm, EmpreendimentoUpdateForm,
                    AtualizarLoteForm)
from .models import Empreendimento, Quadra, Lote, TypeLote
from accounts.models import User, UsuarioEmpreendimento
from vendas.models import RegisterVenda
from documentos.models import ModeloDocumento, EmpreendimentoDocumento


from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image
)



@has_permission_decorator('selectEmpreendimento')
def selectEmpreendimento(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)


@has_permission_decorator('criarEmpreendimento')
def criarEmpreendimento(request):
    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return render(request, 'empreendimento.html', {
                'form': form,
            })

        try:
            with transaction.atomic():

                empreendimento = form.save()

                # =========================
                # Salvar Imagens
                # =========================
                files = request.FILES.getlist('Empreendimento')
                erros = []

                for file in files:
                    if not file.content_type.startswith('image/'):
                        erros.append(f"{file.name} não é uma imagem válida.")
                        continue

                    img = ImagemEmpreendimento(
                        empreendimento=empreendimento,
                        imagem=file
                    )

                    try:
                        img.full_clean()
                        img.save()
                    except ValidationError as e:
                        erros.append(f"Erro na imagem {file.name}: {e}")

                messages.success(request, "Empreendimento criado com sucesso!")

                if erros:
                    messages.warning(
                        request,
                        "Algumas imagens não foram salvas:\n" + "\n".join(erros)
                    )

                return redirect('lista-empreendimento-tabela')

        except Exception as e:
            messages.error(request, f"Erro ao criar empreendimento: {e}")

    # =========================
    # GET
    # =========================
    return render(request, 'empreendimento.html', {
        'form': EmpreendimentoForm(),
    })



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


@has_permission_decorator('listaQuadra')
def listaQuadra(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    situacao_filtro = request.GET.get('situacao')

    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Inicializa a consulta de quadras
    quadras = Quadra.objects.filter(empr=empreendimento).order_by('id')

    quadras_info_list = []

    for quadra in quadras:
        # Filtra os lotes diretamente aqui, com base na situação, se existir
        lotes = quadra.lotes.all()

        if situacao_filtro and situacao_filtro != 'TODOS':
            if situacao_filtro == 'OUTROS':
                lotes = lotes.filter(
                    Q(situacao='CONSTRUTORA') |
                    Q(situacao='EM_RESERVA') |
                    Q(situacao='INDISPONIVEL')
                )
            else:
                lotes = lotes.filter(situacao=situacao_filtro)

        # Se não houver lotes após o filtro, pula para a próxima quadra
        if not lotes.exists():
            continue

        total_livres = lotes.filter(situacao="DISPONIVEL").count()
        total_vendidos = lotes.filter(situacao="VENDIDO").count()
        outros = lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='EM_RESERVA') |
            Q(situacao='INDISPONIVEL')
        ).count()

        lotes_info = []

        for lote in lotes:
            try:
                area = Decimal(str(lote.area or "0").replace(",", "."))
                valor_metro = Decimal(str(lote.valor_metro_quadrado or "0").replace(",", "."))

                quantidade_parcela = lote.quadra.empr.quantidade_parcela or 0
                quantidade_parcela = int(quantidade_parcela)

                valor_total = area * valor_metro

                if quantidade_parcela > 0:
                    valor_parcela = (valor_total / Decimal(quantidade_parcela)).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP
                    )
                else:
                    valor_parcela = Decimal("0.00")

            except (TypeError, ValueError, InvalidOperation, AttributeError):
                valor_parcela = Decimal("0.00")

            lotes_info.append({
                "lote": lote,
                "situacao": lote.situacao,
                "valor_parcela_formatado": formatar_moeda(valor_parcela),
            })



        quadras_info_list.append({
            'quadra': quadra,
            'total_livres': total_livres,
            'total_vendidos': total_vendidos,
            'lotes': lotes_info,
            'outros': outros
        })

    # Paginação
    paginator = Paginator(quadras_info_list, 9)
    page = request.GET.get('page')

    try:
        quadras_info_page = paginator.page(page)
    except PageNotAnInteger:
        quadras_info_page = paginator.page(1)
    except EmptyPage:
        quadras_info_page = paginator.page(paginator.num_pages)

    # Estatísticas gerais
    all_lotes = Lote.objects.filter(quadra__empr=empreendimento)

    querydict = request.GET.copy()  # Torna o QueryDict mutável

    if 'page' in querydict:
        querydict.pop('page')  # Remove o parâmetro 'page'

    context = {
        'quadras_info': quadras_info_page,
        'empreendimento': empreendimento,
        'total': all_lotes.count(),
        'livre': all_lotes.filter(situacao='DISPONIVEL').count(),
        'prereserva': all_lotes.filter(situacao='PRE-RESERVA').count(),
        'reservado': all_lotes.filter(situacao='RESERVADO').count(),
        'pre_venda': all_lotes.filter(situacao='PRE-VENDA').count(),
        'vendido': all_lotes.filter(situacao='VENDIDO').count(),
        'analise': all_lotes.filter(situacao='ANALISE').count(),
        'outros': all_lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='INDISPONIVEL')
        ).count(),
        'situacao_filtro': situacao_filtro,
        'querystring': querydict.urlencode()
    }

    return render(request, 'lista-quadras.html', context)


@has_permission_decorator('atualizarLotes')
def atualizarLotes(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    quadra = request.GET.get('quadra', '').strip()
    lote = request.GET.get('lote', '').strip()

    lotes = Lote.objects.select_related('quadra', 'quadra__empr').filter(
        quadra__empr=empreendimento
    ).order_by(
        'id',
        'quadra__namequadra',
        'lote'
    )

    if quadra:
        lotes = lotes.filter(quadra__namequadra__iexact=quadra)

    if lote:
        lotes = lotes.filter(lote__iexact=lote)

    paginator = Paginator(lotes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    querydict = request.GET.copy()
    querydict.pop('page', None)

    context = {
        'lotes': page_obj,
        'page_obj': page_obj,
        'empreendimento': empreendimento,
        'filtro_quadra': quadra,
        'filtro_lote': lote,
        'querystring': querydict.urlencode(),
    }
    return render(request, 'atualizar-lotes.html', context)


@has_permission_decorator('atualizarLotes')
def editarAtualizarLote(request, lote_uuid):
    lote = get_object_or_404(Lote.objects.select_related('quadra', 'quadra__empr'), uuid=lote_uuid)
    querystring = request.GET.urlencode()

    if request.method == 'POST':
        form = AtualizarLoteForm(request.POST, instance=lote)
        querystring = request.POST.get('querystring', '')

        if form.is_valid():
            form.save()
            messages.success(request, "Lote atualizado com sucesso!")
            url = reverse('atualizar-lotes', args=[lote.quadra.empr.uuid])
            if querystring:
                url = f'{url}?{querystring}'
            return redirect(url)

        messages.error(request, "Verifique os campos informados.")
    else:
        form = AtualizarLoteForm(instance=lote)

    context = {
        'form': form,
        'lote': lote,
        'querystring': querystring,
    }
    return render(request, 'editar-atualizar-lote.html', context)


class importarDados(View):
    template_name = 'empreendimento_arq.html'

    def get(self, request, uuid, *args, **kwargs):
        empreendimento = get_object_or_404(Empreendimento, uuid=uuid)
        form = ArquivoForm()
        context = {'form': form, 'empreendimento': empreendimento}
        return render(request, self.template_name, context)

    def post(self, request, uuid):
        empreendimento = get_object_or_404(Empreendimento, uuid=uuid)
        form = ArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['arquivo']

            # Lê o Excel a partir da terceira linha (pulando as duas primeiras)
            df = pd.read_excel(arquivo, skiprows=1,
                               names=["quadra", "lote", "area", "valor_metro_quadrado", "situacao"])

            # Remover linhas vazias
            df = df.dropna(subset=["quadra", "lote", "area", "valor_metro_quadrado"])

            # Converter os valores para string para evitar problemas
            df["quadra"] = df["quadra"].astype(str).str.strip()
            df["lote"] = df["lote"].astype(str).str.strip()

            # Iterar sobre as linhas do DataFrame e criar registros
            for _, row in df.iterrows():
                self.criar_quadra(row, empreendimento.id)
            messages.success(request, "Arquivo importado com sucesso!")
            return redirect('lista-empreendimento-tabela')  # Ajuste para onde quer redirecionar

        return render(request, self.template_name, {'form': form})

    def criar_quadra(self, row, empreendimento_id):
        quadra, _ = Quadra.objects.get_or_create(
            namequadra=row["quadra"],
            empr_id=empreendimento_id  # Supondo que 'empr' seja uma ForeignKey para 'empreendimento'
        )

        # Criar o lote com a situação original do arquivo
        Lote.objects.create(
            lote=row["lote"],
            area=row["area"],
            situacao=row["situacao"],  # Mantém o status real do lote
            valor_metro_quadrado=row["valor_metro_quadrado"],
            quadra=quadra
        )


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


from collections import OrderedDict
import math


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


@has_permission_decorator('reservarLote')
def alteraLote(request, uuid):
    lote = get_object_or_404(Lote, uuid=uuid)
    get_tempo = Empreendimento.objects.get(id=lote.quadra.empr_id)

    try:
        area = float(lote.area)
        valor_metro = float(lote.valor_metro_quadrado)
        valor = area * valor_metro
    except (TypeError, ValueError):
        valor = 0

    # Formatação para moeda brasileira
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Pegando a quantidade de parcelas (ajuste o nome conforme seu modelo)
    try:
        total_parcelas = int(get_tempo.quantidade_parcela)
    except (TypeError, ValueError, AttributeError):
        total_parcelas = 0

    # Cálculo do valor da parcela
    if total_parcelas > 0:
        valor_parcela = valor / total_parcelas
    else:
        valor_parcela = 0

    # Formatação do valor da parcela
    valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Caso especial: liberar lote se estiver em reserva mas sem lógica de uso (defensivo)
    if lote.situacao == "EM_RESERVA" and not lote.user:
        lote.situacao = "DISPONIVEL"
        lote.save()
        messages.error(request, "Pre-Reservado Cancelada!")

    if request.method == 'GET':
        # Ao acessar, define como EM_RESERVA
        if lote.situacao == "DISPONIVEL":
            lote.situacao = "EM_RESERVA"
            lote.tempo_reservado = timezone.now() + timedelta(days=lote.quadra.empr.tempo_reserva)
            lote.save()
        form = LoteForm(instance=lote)
        context = {'form': form,
                   'lote': lote,
                   'valor_formatado': valor_formatado,
                   'valor_parcela_formatado': valor_parcela_formatado,
                   'total_parcelas': total_parcelas}
        return render(request, 'reserva-temporaria.html', context)

    elif request.method == 'POST':
        form = LoteForm(request.POST, request.FILES, instance=lote)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.situacao = 'PRE-RESERVA'
            lote.data_termina_reserva = timezone.now() + timedelta(days=lote.quadra.empr.tempo_reserva)
            lote.user = request.user.first_name
            lote.telefone_user = request.user.contato
            lote.save()
            messages.success(request, "Pre-Reservado Salva Com Sucesso!")
            return redirect('listar-quadras', uuid=lote.quadra.empr_uuid)

        else:
            context = {'form': form,
                       'lote': lote,
                       'valor_formatado': valor_formatado,
                       'valor_parcela_formatado': valor_parcela_formatado,
                       'total_parcelas': total_parcelas}
            return render(request, 'reserva-temporaria.html', context)


@has_permission_decorator('reservadoDetalheEmpreendimento')
def reservadoDetalheEmpreendimento(request, preReserva_uuid):
    #lote = Lote.objects.filter(uuid=preReserva_uuid).first()

    lote = None

    from django.http import HttpResponseForbidden

    if not request.user.is_authenticated:
        lote = Lote.objects.filter(uuid=preReserva_uuid).first()
        context = {'lote': lote}
        return render(request, 'permissao.html', context)
        #return HttpResponseForbidden("Você não tem permissão.")

    if request.user.tipo_usuario == "ADMINISTRADOR":
        lote = Lote.objects.filter(uuid=preReserva_uuid).first()
    else:
        lote = Lote.objects.filter(
            uuid=preReserva_uuid,
            user=request.user.first_name
        ).first()

    if not lote:
        lote = Lote.objects.filter(uuid=preReserva_uuid).first()

        context = {'lote': lote}
        return render(request, 'permissao.html', context)
        #return HttpResponseForbidden("Você não tem permissão para acessar este lote.")

    context = {'lote': lote}

    return render(request, 'detalhes-reserva-lote.html', context)


@has_permission_decorator('listaReservasTemporaria')
def listaReservasTemporaria(request):
    query = request.GET.get('q', '')
    tipo_empreendimento = request.GET.get('tipo_empreendimento', '')

    # Filtra lotes 'PRE-RESERVA'
    lotes = Lote.objects.filter(situacao='PRE-RESERVA')

    if query:
        lotes = lotes.filter(
            Q(quadra__empr__nome__icontains=query) |
            Q(quadra__nome__icontains=query) |
            Q(numero__icontains=query) |
            Q(user__username__icontains=query)
        )

    if tipo_empreendimento:
        lotes = lotes.filter(quadra__empr__id=tipo_empreendimento)

    paginator = Paginator(lotes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    empreendimentos = Empreendimento.objects.filter(is_ativo=False).order_by('id')

    context = {
        'page_obj': page_obj,
        'query': query,
        'tipo_empreendimento': tipo_empreendimento,
        'empreendimentos': empreendimentos,
    }
    return render(request, 'relatorio_de_reservas_temporario.html', context)


# @has_permission_decorator('liberaLote')
def liberaLote(request, lote_uuid):
    get_lote = get_object_or_404(Lote, uuid=lote_uuid)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.save()
        messages.success(request, "Lote liberado com Sucesso!")
    return redirect('listar-quadras', empreendimento_uuid=get_lote.quadra.empr.uuid)


@has_permission_decorator('cancelarReservadoTemporaria')
def cancelarReservadoTemporaria(request, lote_uuid):
    get_lote = get_object_or_404(Lote, uuid=lote_uuid)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.cliente_reserva = ""
        get_lote.telefone = ""
        get_lote.save()
        messages.error(request, "Pre-Resevado Cancelada!")
    return redirect('listar-quadras', empreendimento_uuid=get_lote.quadra.empr.uuid)


@has_permission_decorator('cancelarReservadoTemporariaLista')
def cancelarReservadoTemporariaLista(request, lote_uuid):
    get_lote = get_object_or_404(Lote, uuid=lote_uuid)

    if request.method == 'GET':
        get_lote.situacao = "DISPONIVEL"
        get_lote.cliente_reserva = ""
        get_lote.telefone = ""
        get_lote.save()
        messages.error(request, "Pre-Resevado Cancelada!")
    return redirect('lista-pre-reserva')


@has_permission_decorator('renovarReservaTemporaria')
def renovaReserva(request, renova_uuid):
    get_lote = Lote.objects.get(uuid=renova_uuid)

    get_lote.data_termina_reserva = datetime.now() + timedelta(days=get_lote.quadra.empr.tempo_reserva)

    get_lote.save()
    messages.success(request, "Reserva renovada com sucesso!")
    return redirect('lista-pre-reserva')

def gerarRelatorioLotes(request):

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="relatorio_lotes.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    # filtros
    situacao = request.GET.get('situacao', 'TODOS')
    loteamento_uuid = request.GET.get('loteamento_uuid')
    empreendimento = None

    if loteamento_uuid:
        empreendimento = Empreendimento.objects.filter(uuid=loteamento_uuid).first()

    # consulta inicial
    lotes = Lote.objects.select_related(
        'quadra',
        'quadra__empr'
    ).all()

    if empreendimento:
        lotes = lotes.filter(
            quadra__empr=empreendimento
        )

    # filtra situação se não for TODOS
    if situacao != 'TODOS':
        if situacao == 'OUTROS':
            lotes = lotes.filter(
                Q(situacao='CONSTRUTORA') |
                Q(situacao='EM_RESERVA') |
                Q(situacao='INDISPONIVEL')
            )
        else:
            lotes = lotes.filter(situacao=situacao)

    # nome empreendimento
    primeiro_lote = lotes.first()

    nome_empreendimento = (
        empreendimento.nome
        if empreendimento
        else primeiro_lote.quadra.empr.nome
        if primeiro_lote
        else 'Empreendimento nao identificado'
    )
    title_style = ParagraphStyle(
        'RelatorioLotesTitle',
        parent=styles['Title'],
        alignment=1,
        fontSize=18,
        leading=22,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'RelatorioLotesSubtitle',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        spaceAfter=12
    )

    if empreendimento and empreendimento.logo:
        try:
            logo_data = BytesIO(empreendimento.logo.read())
            logo = Image(logo_data)
            logo.drawHeight = 58
            logo.drawWidth = 150
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 12))
        except Exception:
            pass

    titulo = Paragraph(
        f'Relatorio de Lotes - <b>{nome_empreendimento}</b>',
        title_style
    )

    elementos.append(titulo)
    elementos.append(Spacer(1, 10))

    subtitulo = Paragraph(
        f'Situacao dos Lotes: <b>{situacao}</b>',
        subtitle_style
    )

    elementos.append(subtitulo)
    elementos.append(Spacer(1, 10))

    dados = [[
        'Quadra',
        'Lote',
        'Situacao',
        'Valor do Lote'
    ]]

    def formatar_moeda(valor):
        return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    def calcular_valor_lote(lote):
        try:
            area = float(str(lote.area or 0).replace(',', '.'))
            valor_metro = float(str(lote.valor_metro_quadrado or 0).replace(',', '.'))
            return area * valor_metro
        except (TypeError, ValueError):
            return 0

    for lote in lotes:
        dados.append([
            lote.quadra.namequadra,
            lote.lote,
            lote.situacao,
            formatar_moeda(calcular_valor_lote(lote))
        ])

    tabela = Table(
        dados,
        colWidths=[105, 105, 150, 160],
        repeatRows=1
    )

    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#08789A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#9CA3AF')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabela)

    doc.build(elementos)

    return response

"""def gerarRelatorioLotes(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_lotes.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    # Filtros
    situacao = request.GET.get('situacao', 'TODOS')
    loteamento_uuid = request.GET.get('loteamento_uuid')
    empreendimento = None

    if loteamento_uuid:
        empreendimento = Empreendimento.objects.filter(uuid=loteamento_uuid).first()

    # Aplica os filtros
    lotes = Lote.objects.all()
    if loteamento_uuid:
        lotes = lotes.filter(quadra__empr__uuid=loteamento_uuid)
    if situacao != 'TODOS':
        if situacao == 'OUTROS':
            lotes = lotes.filter(
                Q(situacao='CONSTRUTORA') |
                Q(situacao='EM_RESERVA') |
                Q(situacao='INDISPONIVEL')
            )
        else:
            lotes = lotes.filter(situacao=situacao)

    # Verifica se há pelo menos um lote
    primeiro_lote = lotes.first()
    nome_empreendimento = primeiro_lote.quadra.empr.nome if primeiro_lote else "Empreendimento não identificado"

    # Título
    titulo = Paragraph(f"Relatório de Lotes - <b>{nome_empreendimento}</b>", styles['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    # Subtítulo
    subtitulo = Paragraph(f"Situação dos Lotes: <b>{situacao}</b>", styles['Heading2'])
    elementos.append(subtitulo)
    elementos.append(Spacer(1, 12))

    # Cabeçalho da tabela
    dados = [['Quadra', 'Lote', 'Situação', 'Vencimento da Reserva', 'Corretor']]

    for lote in lotes:
        dados.append([
            lote.quadra.namequadra,
            lote.lote,
            lote.situacao,
            lote.data_termina_reserva.strftime('%d/%m/%Y') if lote.data_termina_reserva else '',
            lote.user
        ])

    # Tabela formatada
    tabela = Table(dados, colWidths=[90, 90, 120, 180])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#036B91")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (1, 1), (-1, -1), 6),
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    return response"""


@require_POST
def criarUsuarioEmpreendimento(request):
    empreendimento_id = request.POST.get('empreendimento')
    users_ids = request.POST.getlist('users')

    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    if not users_ids:
        messages.warning(request, 'Selecione pelo menos um corretor para adicionar.')
        return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)

    usuarios = User.objects.filter(id__in=users_ids)

    adicionados = 0
    reativados = 0

    for usuario in usuarios:
        vinculo, created = UsuarioEmpreendimento.objects.get_or_create(
            empreendimento=empreendimento,
            usuario=usuario,
            defaults={'ativo': True}
        )

        if created:
            adicionados += 1

        elif not vinculo.ativo:
            vinculo.ativo = True
            vinculo.save(update_fields=['ativo'])
            reativados += 1

    if adicionados or reativados:
        messages.success(request, 'Corretor(es) vinculado(s) com sucesso.')
    else:
        messages.info(request, 'Os corretores selecionados já estavam vinculados.')

    return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)

    return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)
"""@require_http_methods(["POST"])
def criarUsuarioEmpreendimento(request):
    users_ids = request.POST.getlist('users')  # Lista de usuários
    empreendimento_id = request.POST.get('empreendimento')

    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    for user_id in users_ids:
        usuario = get_object_or_404(User, id=user_id)

        usuario_empreendimento, created = UsuarioEmpreendimento.objects.get_or_create(
            usuario=usuario,
            empreendimento=empreendimento,
            defaults={'ativo': True}
        )

        if not created:
            usuario_empreendimento.ativo = True
            usuario_empreendimento.save()

    messages.success(request, "Usuários adicionados com sucesso!")
    return redirect('detalhe-empreendimento', id=empreendimento.id)"""

@has_permission_decorator('deleteUsuarioEmpreendimento')
@require_POST
def deleteUsuarioEmpreendimento(request, usuario_empreendimento_uuid):
    vinculo = get_object_or_404(UsuarioEmpreendimento, uuid=usuario_empreendimento_uuid)

    empreendimento_uuid = vinculo.empreendimento.uuid

    vinculo.ativo = False
    vinculo.save(update_fields=['ativo'])

    messages.success(request, 'Corretor removido com sucesso.')

    return redirect('detalhe-empreendimento', uuid=empreendimento_uuid)


@require_POST
@login_required
def modelo_vincular(request, empreendimento_uuid):
    empreendimento = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    modelo_id = request.POST.get('modelo_id')
    padrao = request.POST.get('padrao') == '1'

    modelo = get_object_or_404(ModeloDocumento, pk=modelo_id)

    try:
        vinculo, created = EmpreendimentoDocumento.objects.get_or_create(
            empreendimento=empreendimento,
            modelo=modelo,
            defaults={'padrao': padrao, 'ativo': True},
        )
        if not created:
            messages.warning(request, 'Modelo já vinculado.')
        else:
            if padrao:
                # Garante que só um padrão por tipo
                EmpreendimentoDocumento.objects.filter(
                    empreendimento=empreendimento,
                    modelo__tipo=modelo.tipo,
                    padrao=True,
                ).exclude(pk=vinculo.pk).update(padrao=False)
            messages.success(request, f'Modelo "{modelo.titulo}" vinculado.')
    except Exception as e:
        messages.error(request, str(e))

    return redirect('detalhe-empreendimento', uuid=empreendimento.uuid)


@require_POST
@login_required
def modelo_desvincular(request, empreendimento_uuid, vinculo_uuid):
    vinculo = get_object_or_404(EmpreendimentoDocumento, uuid=vinculo_uuid, empreendimento__uuid=empreendimento_uuid)
    empreendimento_uuid = vinculo.empreendimento.uuid
    vinculo.delete()
    messages.success(request, 'Modelo desvinculado.')
    return redirect('detalhe-empreendimento', uuid=empreendimento_uuid)


@require_POST
@login_required
def modelo_set_padrao(request, empreendimento_uuid, vinculo_uuid):
    vinculo = get_object_or_404(EmpreendimentoDocumento, uuid=vinculo_uuid, empreendimento__uuid=empreendimento_uuid)
    # Remove padrão dos outros do mesmo tipo
    EmpreendimentoDocumento.objects.filter(
        empreendimento_id=vinculo.empreendimento_id,
        modelo__tipo=vinculo.modelo.tipo,
        padrao=True,
    ).update(padrao=False)
    vinculo.padrao = True
    vinculo.save(update_fields=['padrao'])
    messages.success(request, f'"{vinculo.modelo.titulo}" definido como padrão.')
    return redirect('detalhe-empreendimento', uuid=vinculo.empreendimento.uuid)


# ===================================================================
# Exportar / Importar Lotes em massa (xlsx)
# ===================================================================

_VENDA_ATIVA_TIPOS = {'ANALISE', 'PRE-VENDA'}
_STATUS_LOTE_VALIDOS = set(TypeLote.values)


def _lote_tem_venda_ativa(lote):
    return RegisterVenda.objects.filter(
        lote=lote,
        tipo_venda__in=_VENDA_ATIVA_TIPOS,
    ).exists()


@has_permission_decorator('atualizarLotes')
def exportar_lotes(request, empreendimento_uuid):
    empr = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    lotes = (
        Lote.objects
        .filter(quadra__empr=empr)
        .select_related('quadra')
        .order_by('quadra__namequadra', 'lote')
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Lotes'

    header_fill = PatternFill(fill_type='solid', fgColor='0F3460')
    header_font = Font(color='FFFFFF', bold=True)
    locked_fill = PatternFill(fill_type='solid', fgColor='D3D3D3')

    headers = ['id', 'numero', 'quadra', 'area', 'preco', 'status', 'descricao', 'cliente_reserva']
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    for row_idx, lote in enumerate(lotes, 2):
        bloqueado = _lote_tem_venda_ativa(lote)
        ws.cell(row=row_idx, column=1, value=lote.id)
        ws.cell(row=row_idx, column=2, value=lote.lote)
        ws.cell(row=row_idx, column=3, value=lote.quadra.namequadra)
        ws.cell(row=row_idx, column=4, value=lote.area)
        ws.cell(row=row_idx, column=5, value=lote.valor_metro_quadrado)
        status_cell = ws.cell(
            row=row_idx, column=6,
            value='[BLOQUEADO]' if bloqueado else lote.situacao,
        )
        if bloqueado:
            status_cell.fill = locked_fill
        ws.cell(row=row_idx, column=7, value=lote.medidasConfrontacoes or '')
        ws.cell(row=row_idx, column=8, value=lote.cliente_reserva or '')

    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = max(max_len + 4, 12)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    date_str = date.today().strftime('%Y-%m-%d')
    nome_safe = re.sub(r'[^\w\s-]', '', empr.nome).strip().replace(' ', '_')
    filename = f'lotes_{nome_safe}_{date_str}.xlsx'

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@has_permission_decorator('atualizarLotes')
@require_http_methods(['POST'])
def importar_lotes(request, empreendimento_uuid):
    empr = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        messages.error(request, 'Selecione um arquivo xlsx.')
        return redirect(reverse('detalhe-empreendimento', args=[empr.uuid]))

    try:
        wb = openpyxl.load_workbook(arquivo, data_only=True)
        ws = wb.active
    except Exception:
        messages.error(request, 'Arquivo inválido. Envie um xlsx gerado pela exportação.')
        return redirect(reverse('detalhe-empreendimento', args=[empr.uuid]))

    ids_empr = set(
        Lote.objects.filter(quadra__empr=empr).values_list('id', flat=True)
    )

    alteracoes = []
    ignorados = []
    erros = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if not any(cell is not None for cell in row):
            continue

        row_padded = (list(row) + [None] * 8)[:8]
        lote_id_raw, numero, quadra_nome, area, preco, status, descricao, cliente_reserva_val = row_padded

        if lote_id_raw is None:
            erros.append({'linha': row_idx, 'motivo': 'ID ausente'})
            continue

        try:
            lote_id = int(lote_id_raw)
        except (TypeError, ValueError):
            erros.append({'linha': row_idx, 'motivo': f'ID inválido: {lote_id_raw}'})
            continue

        if lote_id not in ids_empr:
            erros.append({
                'linha': row_idx,
                'motivo': f'Lote id={lote_id} não pertence a este empreendimento',
            })
            continue

        try:
            lote = Lote.objects.select_related('quadra').get(id=lote_id)
        except Lote.DoesNotExist:
            erros.append({'linha': row_idx, 'motivo': f'Lote id={lote_id} não encontrado'})
            continue

        if _lote_tem_venda_ativa(lote):
            ignorados.append({'id': lote_id, 'numero': lote.lote, 'motivo': 'venda ativa'})
            continue

        campos = {}

        if area is not None:
            area_str = str(area).strip()
            if area_str != str(lote.area or '').strip():
                campos['area'] = {'atual': lote.area or '', 'novo': area_str}

        if preco is not None:
            preco_str = str(preco).strip()
            try:
                preco_val = Decimal(preco_str.replace(',', '.'))
            except InvalidOperation:
                erros.append({'linha': row_idx, 'motivo': f'Preço inválido: {preco_str}'})
                continue
            if preco_val < 0:
                erros.append({'linha': row_idx, 'motivo': f'Preço negativo: {preco_str}'})
                continue
            if preco_str != str(lote.valor_metro_quadrado or '').strip():
                campos['valor_metro_quadrado'] = {
                    'atual': str(lote.valor_metro_quadrado or ''),
                    'novo': preco_str,
                }

        if status is not None:
            status_str = str(status).strip()
            if status_str not in ('[BLOQUEADO]', ''):
                if status_str not in _STATUS_LOTE_VALIDOS:
                    erros.append({
                        'linha': row_idx,
                        'motivo': (
                            f'Status inválido: "{status_str}". '
                            f'Válidos: {", ".join(sorted(_STATUS_LOTE_VALIDOS))}'
                        ),
                    })
                    continue
                if status_str != lote.situacao:
                    campos['situacao'] = {'atual': lote.situacao, 'novo': status_str}

        if descricao is not None:
            descricao_str = str(descricao).strip()
            atual = (lote.medidasConfrontacoes or '').strip()
            if descricao_str != atual:
                campos['medidasConfrontacoes'] = {'atual': atual, 'novo': descricao_str}

        if cliente_reserva_val is not None:
            cr_str = str(cliente_reserva_val).strip()
            atual_cr = (lote.cliente_reserva or '').strip()
            if cr_str != atual_cr:
                campos['cliente_reserva'] = {'atual': atual_cr, 'novo': cr_str}

        if campos:
            alteracoes.append({'id': lote_id, 'numero': lote.lote, 'campos': campos})

    context = {
        'empreendimento': empr,
        'alteracoes': alteracoes,
        'ignorados': ignorados,
        'erros': erros,
        'alteracoes_json': json.dumps(alteracoes),
    }
    return render(request, 'importar-lotes-preview.html', context)


@has_permission_decorator('atualizarLotes')
@require_POST
def importar_lotes_confirmar(request, empreendimento_uuid):
    empr = get_object_or_404(Empreendimento, uuid=empreendimento_uuid)
    try:
        alteracoes = json.loads(request.POST.get('alteracoes_json', '[]'))
    except json.JSONDecodeError:
        messages.error(request, 'Dados inválidos. Refaça a importação.')
        return redirect(reverse('detalhe-empreendimento', args=[empr.uuid]))

    ids_empr = set(
        Lote.objects.filter(quadra__empr=empr).values_list('id', flat=True)
    )
    campos_permitidos = {'area', 'valor_metro_quadrado', 'situacao', 'medidasConfrontacoes', 'cliente_reserva'}

    atualizados = 0
    ignorados = 0
    with transaction.atomic():
        for alt in alteracoes:
            try:
                lote_id = int(alt['id'])
            except (KeyError, TypeError, ValueError):
                continue
            if lote_id not in ids_empr:
                continue
            try:
                lote = Lote.objects.get(id=lote_id)
            except Lote.DoesNotExist:
                continue
            if _lote_tem_venda_ativa(lote):
                ignorados += 1
                continue

            campos = alt.get('campos', {})
            update_fields = []
            for field, valores in campos.items():
                if field in campos_permitidos:
                    setattr(lote, field, valores.get('novo', ''))
                    update_fields.append(field)

            if update_fields:
                lote.save(update_fields=update_fields)
                atualizados += 1

    partes = [f'✅ {atualizados} lotes atualizados']
    if ignorados:
        partes.append(f'⚠️ {ignorados} ignorados (venda ativa)')
    messages.success(request, ' — '.join(partes))
    return redirect(reverse('detalhe-empreendimento', args=[empr.uuid]))

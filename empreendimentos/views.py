from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils.http import urlencode

from rolepermissions.decorators import has_permission_decorator

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views import View

from django.utils import timezone
from .forms import EmpreendimentoForm, ArquivoForm
from .models import Empreendimento, Quadra, Lote
from accounts.models import User, UsuarioEmpreendimento


@has_permission_decorator('selectEmpreendimento')
def selectEmpreendimento(request, empreendimento_id):
    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)


@has_permission_decorator('criarEmpreendimento')
def criarEmpreendimento(request):
    form = EmpreendimentoForm()

    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                empreendimento = form.save()
                files = request.FILES.getlist('Empreendimento')

                imagens_criadas = []
                erros = []

                for file in files:
                    if file.content_type.startswith('image/'):
                        img = ImagemEmpreendimento(empreendimento=empreendimento, imagem=file)
                        try:
                            img.full_clean()  # Validações do Django
                            img.save()
                            imagens_criadas.append(file.name)
                        except ValidationError as e:
                            erros.append(f"Erro ao salvar {file.name}: {e}")
                    else:
                        erros.append(f"O arquivo {file.name} não é uma imagem válida.")

                # Exibir mensagens apropriadas
                if imagens_criadas:
                    messages.success(request,
                                     f"Empreendimento criado com sucesso! Imagens adicionadas: {', '.join(imagens_criadas)}")
                if erros:
                    messages.warning(request, "Algumas imagens não foram salvas:\n" + "\n".join(erros))

                return redirect('lista-empreendimento-tabela')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao criar o empreendimento: {e}")

    return render(request, 'empreendimento.html', {'form': form})


@has_permission_decorator('listaEmpreendimento')
def listaEmpreendimento(request):
    # Filtrando os empreendimentos que estão inativos e vinculados ao usuário logado
    empreendimentos_ids = UsuarioEmpreendimento.objects.filter(usuario=request.user, ativo=True).values_list(
        'empreendimento_id',
        flat=True)
    empreendimentos = Empreendimento.objects.filter(id__in=empreendimentos_ids, is_ativo=False)

    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos.html', context)


@has_permission_decorator('alterarEmpreendimento')
def alteraEmpreendimento(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)

    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES, instance=empreendimento)

        if form.is_valid():
            form.save()
            return redirect('lista-empreendimento-tabela')
        else:
            context = {'form': form, 'empreendimento': empreendimento}
            return render(request, 'update_empreendimento.html', context)
    else:
        form = EmpreendimentoForm(instance=empreendimento)
        context = {'form': form, 'empreendimento': empreendimento}
        return render(request, 'update_empreendimento.html', context)


@has_permission_decorator('deletarEmpreendimento')
@require_POST
def deleteEmpreendimento(request, empreendimento_Id):
    print(empreendimento_Id)
    empreendimento = Empreendimento.objects.get(id=empreendimento_Id)
    empreendimento.is_ativo = True
    empreendimento.save()
    return redirect('lista-empreendimento-tabela')


@has_permission_decorator('listaEmpreendimentoTabela')
def listaEmpreendimentoTabela(request):
    # Buscar empreendimentos que estão ativos
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)

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
            'id': empreendimento.id,
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
        'empreendimentos': empreendimento_info,
    }
    return render(request, 'lista-empreendimentos-tabela.html', context)


"""def listaQuadra(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)
    situacao_filtro = request.GET.get('situacao')

    # Filtra as quadras do empreendimento
    quadras = Quadra.objects.filter(empr=empreendimento).order_by('id')

    # Aplica o filtro de situação se houver
    if situacao_filtro and situacao_filtro != 'TODOS':
        if situacao_filtro == 'OUTROS':
            quadras = quadras.filter(
                Q(situacao='CONSTRUTORA') |
                Q(situacao='EM_RESERVA') |
                Q(situacao='INDISPONIVEL')
            )
        else:
            quadras = quadras.filter(situacao=situacao_filtro)

    quadras_info_list = []

    for quadra in quadras:
        lotes = Lote.objects.filter(quadra=quadra).order_by('id')
        total_livres = lotes.filter(situacao="DISPONIVEL").count()
        total_vendidos = lotes.filter(situacao="VENDIDO").count()
        outros = lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='EM_RESERVA') |
            Q(situacao='INDISPONIVEL')
        ).count()

        lotes_info = [
            {'lote': lote, 'situacao': lote.situacao} for lote in lotes
        ]

        quadras_info_list.append({
            'quadra': quadra,
            'total_livres': total_livres,
            'total_vendidos': total_vendidos,
            'lotes': lotes_info,
            'outros': outros
        })

    # Paginação
    paginator = Paginator(quadras_info_list, 12)
    page = request.GET.get('page')

    try:
        quadras_info_page = paginator.page(page)
    except PageNotAnInteger:
        quadras_info_page = paginator.page(1)
    except EmptyPage:
        quadras_info_page = paginator.page(paginator.num_pages)

    # Estatísticas gerais
    all_lotes = Lote.objects.filter(quadra__empr=empreendimento)

    querydict = request.GET.copy()
    if 'page' in querydict:
        querydict.pop('page')

    context = {
        'quadras_info': quadras_info_page,  # importante!
        'empreendimento': empreendimento,
        'total': all_lotes.count(),
        'livre': all_lotes.filter(situacao='DISPONIVEL').count(),
        'reserva': all_lotes.filter(situacao='RESERVADO').count(),
        'vendido': all_lotes.filter(situacao='VENDIDO').count(),
        'outros': all_lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='EM_RESERVA') |
            Q(situacao='INDISPONIVEL')
        ).count(),
        'situacao_filtro': situacao_filtro,
        'querystring': urlencode(querydict)
    }

    return render(request, 'lista-quadras.html', context)"""


@has_permission_decorator('listaQuadra')
def listaQuadra(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)
    situacao_filtro = request.GET.get('situacao')

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

        lotes_info = [{'lote': lote, 'situacao': lote.situacao} for lote in lotes]

        quadras_info_list.append({
            'quadra': quadra,
            'total_livres': total_livres,
            'total_vendidos': total_vendidos,
            'lotes': lotes_info,
            'outros': outros
        })

    # Paginação
    paginator = Paginator(quadras_info_list, 12)
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
        'reserva': all_lotes.filter(situacao='EM_RESERVA').count(),
        'vendido': all_lotes.filter(situacao='VENDIDO').count(),
        'outros': all_lotes.filter(
            Q(situacao='CONSTRUTORA') |
            Q(situacao='INDISPONIVEL')
        ).count(),
        'situacao_filtro': situacao_filtro,
        'querystring': querydict.urlencode()
    }

    return render(request, 'lista-quadras.html', context)


class importarDados(View):
    template_name = 'empreendimento_arq.html'

    def get(self, request, id, *args, **kwargs):
        empreendimento = Empreendimento.objects.get(id=id)
        form = ArquivoForm()
        context = {'form': form, 'empreendimento': empreendimento}
        return render(request, self.template_name, context)

    def post(self, request, id):
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
                self.criar_quadra(row, id)
            messages.success(request, "Arquivo importado com sucesso!")
            return redirect('lista-empreendimento-tabela')  # Ajuste para onde quer redirecionar

        return render(request, self.template_name, {'form': form})

    def criar_quadra(self, row, id):
        quadra, _ = Quadra.objects.get_or_create(
            namequadra=row["quadra"],
            empr_id=id  # Supondo que 'empr' seja uma ForeignKey para 'empreendimento'
        )

        # Criar o lote com a situação original do arquivo
        Lote.objects.create(
            lote=row["lote"],
            area=row["area"],
            situacao=row["situacao"],  # Mantém o status real do lote
            valor_metro_quadrado=row["valor_metro_quadrado"],
            quadra=quadra
        )


def detalheEmpreendimento(request, id):
    template_name = 'detalhes-do-empreendimento.html'

    usuarios = User.objects.all()

    empreendimento = Empreendimento.objects.get(id=id)
    corretores = UsuarioEmpreendimento.objects.filter(empreendimento=id, ativo=True)

    # Filtra apenas os lotes desse empreendimento
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

    context = {
        'empreendimento': empreendimento,
        'corretores': corretores,
        'usuarios': usuarios,
        'total': total,
        'livre': livre,
        'reserva': reserva,
        'vendido': vendido,
        'outros': outros
    }

    return render(request, template_name, context)


from collections import OrderedDict
import math


def relatorioFinanceiro(request, id):
    template_name = 'relatorio-financeiro.html'

    empreendimento = Empreendimento.objects.get(id=id)

    lotes = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO') | Q(situacao='VENDIDO'))
    lotes_disponiveis = Lote.objects.filter(quadra__empr_id=empreendimento.id).filter(Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')
    )
    lotes_vendidos = Lote.objects.filter(quadra__empr_id=id, situacao='VENDIDO')

    quantidade_lotes = Lote.objects.filter(quadra__empr_id=id).count()
    quantidade_lotes_disponivel = Lote.objects.filter(quadra__empr_id=id).filter(Q(situacao='DISPONIVEL') | Q(situacao='RESERVADO')).count()
    quantidade_lotes_vendidos = Lote.objects.filter(quadra__empr_id=id, situacao='VENDIDO').count()
    quantidade_lotes_indisponivel = Lote.objects.filter(quadra__empr_id=id).filter(Q(situacao='CONSTRUTORA') | Q(situacao='INDISPONIVEL')).count()


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
        'parcelas_total_vendidos_formatado': parcelas_total_vendidos_formatado


    }

    return render(request, template_name, context)

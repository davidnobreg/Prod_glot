from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from requests import request

from rolepermissions.decorators import has_role_decorator

from django.core.paginator import Paginator
from django.views import View

from .forms import EmpreendimentoForm, ArquivoForm
from .models import Empreendimento, Quadra, Lote


@has_role_decorator('selectEmpreendimento')
def selectEmpreendimento(request, empreendimento_id):
    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)


@has_role_decorator('criarEmpreendimento')
def criarEmpreendimento(request):
    form = EmpreendimentoForm()

    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)
        if form.is_valid():
            empr = form.save()
            files = request.FILES.getlist('immobile')  ## pega todas as imagens
            return redirect('lista-empreendimento-tabela')
    return render(request, 'empreendimento.html', {'form': form})


@has_role_decorator('criarEmpreendimento')
def listaEmpreendimento(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)
    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos.html', context)


@has_role_decorator('alterarEmpreendimento')
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


@has_role_decorator('deletarEmpreendimento')
def deleteEmpreendimento(request, empreendimento_Id):
    print(empreendimento_Id)
    empreendimento = Empreendimento.objects.get(id=empreendimento_Id)
    empreendimento.is_ativo = True
    empreendimento.save()
    return redirect('lista-empreendimento-tabela')


@has_role_decorator('listaEmpreendimentoTabela')
def listaEmpreendimentoTabela(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)

    get_empreendimento = request.GET.get('empreendimento')

    if get_empreendimento:
        empreendimentos = Empreendimento.objects.filter(nome=get_empreendimento)

    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos-tabela.html', context)


@has_role_decorator('listaQuadra')
def listaQuadra(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)
    quadras = Quadra.objects.filter(empr=empreendimento).order_by('id')

    quadras_info = []  # Lista para armazenar informações sobre quadras e seus lotes

    # Iterar sobre as quadras e associar os lotes de cada uma
    for quadra in quadras:
        total_livres = Lote.objects.filter(quadra=quadra, situacao="DISPONIVEL").count()
        total_vendidos = Lote.objects.filter(quadra=quadra, situacao="VENDIDO").count()

        # Listar os lotes dessa quadra
        lotes = Lote.objects.filter(quadra=quadra).order_by('id')

        lotes_info = []
        for lote in lotes:
            lotes_info.append({
                'lote': lote,
                'situacao': lote.situacao
            })

        # Adiciona as informações da quadra, junto com os lotes dessa quadra
        quadras_info.append({
            'quadra': quadra,
            'total_livres': total_livres,
            'total_vendidos': total_vendidos,
            'lotes': lotes_info  # Lista de lotes dessa quadra
        })

    paginator = Paginator(quadras_info, 5)  # Paginação para as quadras
    page = request.GET.get('page')
    quadras_info = paginator.get_page(page)

    context = {
        'quadras_info': quadras_info,
        'empreendimento': empreendimento
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
            df = pd.read_excel(arquivo, skiprows=2, names=["quadra", "lote", "area", "situacao"])

            # Remover linhas vazias
            df = df.dropna(subset=["quadra", "lote", "area"])

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
            quadra=quadra
        )

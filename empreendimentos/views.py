from django.shortcuts import render, redirect
from django.http import HttpResponse
import pandas as pd
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from django.core.paginator import Paginator
from django.views import View

from .forms import EmpreendimentoForm, ArquivoForm
from .models import Empreendimento, Quadra, Lote


def select_empreendimento(request, empreendimento_id):
    empreendimento = get_object_or_404(Empreendimento, id=empreendimento_id)

    data = {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
    }

    return JsonResponse(data)

def criar_Empreendimento(request):
    form = EmpreendimentoForm() 
    
    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)
        if form.is_valid():
            empr = form.save()
            files = request.FILES.getlist('immobile') ## pega todas as imagens
            return redirect('lista-empreendimento')
    return render(request, 'empreendimento.html', {'form': form})


def lista_Empreendimento(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)
    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos.html', context)

def altera_empreendimento(request, id):
    empreendimento = get_object_or_404(Empreendimento, id=id)

    if request.method == 'GET':
        form = EmpreendimentoForm(instance=empreendimento)  # Preenche o formulário com os dados do empreendimento
        context = {'form': form, 'empreendimento': empreendimento}  # adiciona o cliente no contexto
        return render(request, 'update_empreendimento.html', context)

    if request.method == 'POST':  # Use POST para formulários HTML
        form = EmpreendimentoForm(request.POST, instance=empreendimento)  # Passa os dados e a instância para o formulário

        if form.is_valid():
            form.save()

            return redirect('lista-empreendimento-tabela')  # Redireciona para a lista de clientes

        context = {'form': form, 'empreendimento': empreendimento}  # adiciona o cliente no contexto
        return render(request, 'update_empreendimento.html', context)  # retorna o form com os erros.

    # Se não for GET nem POST, retorna um erro (ou redireciona, dependendo do caso)
    return redirect('lista-empreendimento-tabela')  # redireciona para a lista de clientes, caso o metodo não seja get nem post

def delete_empreendimento(request, id):
    empreendimento = Empreendimento.objects.get(id=id)
    empreendimento.is_ativo=True
    empreendimento.save()
    return redirect('lista-empreendimento-tabela')


def lista_Empreendimento_tabela(request):
    empreendimentos = Empreendimento.objects.filter(is_ativo=False)
    context = {'empreendimentos': empreendimentos}
    return render(request, 'lista-empreendimentos-tabela.html', context)



def lista_Quadra(request, id):
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

class ImportarDadosView(View):
    template_name = 'empreendimento_arq.html'

    def get(self, request, id):
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

            return redirect('lista-empreendimento')  # Ajuste para onde quer redirecionar

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
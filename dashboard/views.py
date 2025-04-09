from django.shortcuts import render,HttpResponse
from empreendimentos.models import Lote
from vendas.models import RegisterVenda

# Create your views here.
def listDashboard(request):
    total = Lote.objects.all().count()
    livre = Lote.objects.filter(situacao='DISPONIVEL').count()
    reservas = RegisterVenda.objects.filter(tipo_venda='RESERVADO').count()
    vendidos = RegisterVenda.objects.filter(tipo_venda='VENDIDO').count()

    context = {
        'total': total,
        'livre': livre,
        'reservas': reservas,
        'vendidos': vendidos,
    }
    return render(request, 'dash.html', context)
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.db.models import Q
from datetime import datetime
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rolepermissions.decorators import has_permission_decorator

from ..models import RegisterVenda
from empreendimentos.models import Empreendimento


@method_decorator(has_permission_decorator('listaVendaRelatorio'), name='dispatch')
class ListarendaRelatorioView(ListView):
    model = RegisterVenda
    template_name = "lista_venda_relatorio.html"
    context_object_name = "vendas"

    paginate_by = 20
    ordering = ['-id']

    def get_queryset(self):

        queryset = RegisterVenda.objects.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user'
        )

        registroVendas = self.request.GET.get("registro")
        get_tipo_venda = self.request.GET.get("tipo_venda")

        if registroVendas:
            queryset = queryset.filter(
                Q(cliente__name__icontains=registroVendas) |
                Q(cliente__documento__icontains=registroVendas) |
                Q(cliente__email__icontains=registroVendas) |
                Q(lote__quadra__empr__nome__icontains=registroVendas) |
                Q(user__username__icontains=registroVendas) |
                Q(user__first_name__icontains=registroVendas) |
                Q(user__last_name__icontains=registroVendas) |
                Q(user__email__icontains=registroVendas)
            )

        if get_tipo_venda:
            queryset = queryset.filter(tipo_venda=get_tipo_venda)

        return queryset.order_by("-id")

@method_decorator(has_permission_decorator('relatorioReserva'), name='dispatch')
class RelatorioReservaView(ListView):

    model = RegisterVenda
    template_name = "lista_reserva.html"
    context_object_name = "reservas"
    paginate_by = 10
    ordering = ['-id']

    def get_queryset(self):
        queryset = RegisterVenda.objects.filter(
            tipo_venda='RESERVADO',
            is_ativo=False
        )

        # 🔎 Filtros
        filtro_empreendimento = self.request.GET.get('tipo_empreendimento')
        filtro_nome = self.request.GET.get('search_nome')
        filtro_tipo_venda = self.request.GET.get('tipo_venda')
        filtro_data_reserva = self.request.GET.get('data_reserva')
        filtro_data_venda = self.request.GET.get('data_venda')

        # 🏢 Empreendimento
        if filtro_empreendimento and filtro_empreendimento.isdigit():
            queryset = queryset.filter(
                lote__quadra__empr__id=int(filtro_empreendimento)
            )

        # 🔍 Busca geral
        if filtro_nome:
            queryset = queryset.filter(
                Q(cliente__name__icontains=filtro_nome) |
                Q(lote__quadra__empr__nome__icontains=filtro_nome) |
                Q(user__username__icontains=filtro_nome)
            )

        # 📅 Data reserva
        if filtro_data_reserva:
            try:
                data = datetime.strptime(filtro_data_reserva, "%Y-%m-%d").date()
                queryset = queryset.filter(dt_reserva=data)
            except ValueError:
                pass

        # 📅 Data venda
        if filtro_data_venda:
            try:
                data = datetime.strptime(filtro_data_venda, "%Y-%m-%d").date()
                queryset = queryset.filter(dt_venda=data)
            except ValueError:
                pass

        # 📌 Tipo venda
        if filtro_tipo_venda:
            queryset = queryset.filter(tipo_venda=filtro_tipo_venda)

        return queryset.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['empreendimentos'] = Empreendimento.objects.filter(
            is_ativo=False
        ).order_by('id')

        # 🔄 Mantém filtros no template
        context['filtros'] = {
            'tipo_empreendimento': self.request.GET.get('tipo_empreendimento', ''),
            'search_nome': self.request.GET.get('search_nome', ''),
            'tipo_venda': self.request.GET.get('tipo_venda', ''),
            'data_reserva': self.request.GET.get('data_reserva', ''),
            'data_venda': self.request.GET.get('data_venda', ''),
        }

        return context



@method_decorator(has_permission_decorator('listaVenda'), name='dispatch')
class ListaVendaView(ListView):

    model = RegisterVenda
    template_name = "lista_venda.html"
    context_object_name = "reservas"
    paginate_by = 10
    ordering = ['-id']

    def get_queryset(self):
        queryset = super().get_queryset()

        venda = self.request.GET.get('venda')
        tipo_venda = self.request.GET.get('tipo_venda')
        tipo_empreendimento = self.request.GET.get('tipo_empreendimento')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        # 🔎 Filtro por empreendimento
        if tipo_empreendimento:
            queryset = queryset.filter(
                lote__quadra__empr__id=tipo_empreendimento,
                lote__quadra__empr__is_ativo=True
            )

        # 🔎 Busca geral
        if venda:
            queryset = queryset.filter(
                Q(cliente__name__icontains=venda) |
                Q(lote__quadra__empr__nome__icontains=venda) |
                Q(user__username__icontains=venda)
            )

        # 🔎 Tipo de venda
        if tipo_venda:
            queryset = queryset.filter(tipo_venda=tipo_venda, is_ativo=False)

        # 🔎 Filtro por data
        try:
            if data_inicio and data_fim:
                dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                queryset = queryset.filter(dt_venda__range=[dt_inicio, dt_fim])

            elif data_inicio:
                dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                queryset = queryset.filter(dt_venda__gte=dt_inicio)

            elif data_fim:
                dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                queryset = queryset.filter(dt_venda__lte=dt_fim)

        except ValueError:
            pass

        return queryset.select_related(
            'cliente',
            'lote',
            'lote__quadra',
            'lote__quadra__empr',
            'user'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['empreendimentos'] = Empreendimento.objects.filter(is_ativo=True).order_by('id')

        # Mantém filtros na tela
        context['filtros'] = {
            'venda': self.request.GET.get('venda', ''),
            'tipo_venda': self.request.GET.get('tipo_venda', ''),
            'tipo_empreendimento': self.request.GET.get('tipo_empreendimento', ''),
            'data_inicio': self.request.GET.get('data_inicio', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
        }

        return context


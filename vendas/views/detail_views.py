from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.http import Http404

from rolepermissions.decorators import has_permission_decorator

from empreendimentos.models import Lote
from vendas.models import RegisterVenda
from clientes.models import ClienteTelefone

@method_decorator(has_permission_decorator('reservado'), name='dispatch')
class ReservadoView(TemplateView):

    template_name = "reservado.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lote_uuid = self.kwargs.get("lote_uuid")

        lote = get_object_or_404(Lote, uuid=lote_uuid)

        # ✅ OneToOne correto
        venda = getattr(lote, 'reg_venda', None)

        cliente_contato = None

        # 🔎 Busca telefone se existir venda
        if venda and venda.cliente:
            cliente_contato = ClienteTelefone.objects.filter(
                cliente=venda.cliente
            ).first()

        # ⚠️ Caso vendido sem registro
        if lote.situacao.lower() == 'vendido' and venda is None:
            context.update({
                'lote': lote,
                'reservas': None,
                'contatoCliente': None
            })
            return context

        context.update({
            'lote': lote,
            'reservas': venda,
            'contatoCliente': cliente_contato
        })

        return context

@method_decorator(has_permission_decorator('analiseReserva'), name='dispatch')
class AnaliseView(TemplateView):

    template_name = "analisa.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lote_uuid = self.kwargs.get("lote_uuid")

        lote = get_object_or_404(Lote, uuid=lote_uuid)

        # ✅ OneToOne correto
        venda = getattr(lote, 'reg_venda', None)

        cliente_contato = None

        # 🔎 Busca telefone se existir venda
        if venda and venda.cliente:
            cliente_contato = ClienteTelefone.objects.filter(
                cliente=venda.cliente
            ).first()

        # ⚠️ Caso analise sem registro
        if lote.situacao.lower() == 'analise' and venda is None:
            context.update({
                'lote': lote,
                'reservas': None,
                'contatoCliente': None
            })
            return context

        area = float(lote.area or 0)
        valor_metro = float(lote.valor_metro_quadrado or 0        )

        valor_lote = area * valor_metro

        context.update({
            'valor_lote': valor_lote,
            'lote': lote,
            'reservas': venda,
            'contatoCliente': cliente_contato
        })

        return context


@method_decorator(
    has_permission_decorator('reservadoDetalhe'),
    name='dispatch'
)
class ReservadoDetalheView(TemplateView):
    template_name = "reservado_detalhe.html"

    # ======================
    # 🔍 BUSCA RESERVA COM REGRA DE ACESSO
    # ======================
    def get_reserva(self):

        reserva_uuid = self.kwargs.get('reserva_uuid')

        queryset = RegisterVenda.objects.select_related('user', 'lote')

        # =========================================
        # NÃO LOGADO → mostra página de permissão
        # =========================================
        if not self.request.user.is_authenticated:
            return None

        # =========================================
        # ADMIN → vê tudo
        # =========================================
        if self.request.user.tipo_usuario == "ADMINISTRADOR":
            return queryset.filter(lote__uuid=reserva_uuid).first()

        # =========================================
        # USUÁRIO NORMAL → só vê o próprio registro
        # =========================================
        return queryset.filter(
            lote__uuid=reserva_uuid,
            user=self.request.user
        ).first()

    # ======================
    # 🧠 CONTEXTO + BLOQUEIO
    # ======================
    def get(self, request, *args, **kwargs):

        reserva = self.get_reserva()

        # =========================================
        # SEM PERMISSÃO
        # =========================================
        if not request.user.is_authenticated or not reserva:
            reserva_uuid = self.kwargs.get('reserva_uuid')

            reserva_publica = RegisterVenda.objects.select_related(
                'user',
                'lote'
            ).filter(
                lote__uuid=reserva_uuid
            ).first()


            context = {
                'contatoNome': reserva_publica.user.first_name,
                'contatoCorretor': (
                    reserva_publica.user.contato
                    if reserva_publica else None
                )
            }

            return render(
                request,
                'permissaoVenda.html',
                context
            )

        # =========================================
        # COM PERMISSÃO
        # =========================================
        context = self.get_context_data(
            reservas=reserva
        )

        context['contatoCorretor'] = (
            reserva.corretor
        )

        return self.render_to_response(context)

    # ======================
    # CONTEXTO NORMAL
    # ======================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context.update(kwargs)

        return context
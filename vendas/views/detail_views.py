from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
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


@method_decorator(
    has_permission_decorator('reservadoDetalhe'),
    name='dispatch'
)
class ReservadoDetalheView(TemplateView):
    template_name = "reservado_detalhe.html"

    # ======================
    # 🔍 BUSCA RESERVA
    # ======================
    def get_reserva(self):
        return get_object_or_404(
            RegisterVenda.objects.select_related('corretor', 'lote'),
            lote__uuid=self.kwargs.get('reserva_uuid')
        )

    # ======================
    # 🧠 CONTEXTO
    # ======================
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            reserva = self.get_reserva()

            context.update({
                'reservas': reserva,
                'contatoCorretor': reserva.corretor
            })

            return context

        except Exception as e:
            print("ERRO:", e)
            raise
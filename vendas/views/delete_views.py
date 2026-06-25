from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.db import transaction
from rolepermissions.decorators import has_permission_decorator


from empreendimentos.models import Lote
from vendas.models import RegisterVenda

@method_decorator(has_permission_decorator('cancelarVenda'), name='dispatch')
class CancelarVendaView(View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        venda = get_object_or_404(RegisterVenda, uuid=kwargs.get('delete_uuid'))

        lote = venda.lote

        # Atualiza lote
        if lote:
            lote.situacao = 'DISPONIVEL'
            lote.save(update_fields=['situacao'])

        # Atualiza venda
        venda.tipo_venda = 'CANCELADA'
        venda.is_ativo = False
        venda.save(update_fields=['tipo_venda', 'is_ativo'])

        messages.success(request, "Venda cancelada com sucesso!")

        return redirect('listar-quadras', empreendimento_uuid=venda.lote.quadra.empr.uuid)




@method_decorator(
    [has_permission_decorator('cancelarReservadoCadastro'), transaction.atomic],
    name='dispatch'
)
class CancelarReservadoCadastroView(View):

    def post(self, request, *args, **kwargs):
        lote = get_object_or_404(Lote, uuid=kwargs.get('cancelaReserva_uuid'))

        # Atualiza situação do lote
        lote.situacao = 'DISPONIVEL'
        lote.save(update_fields=['situacao'])

        # Atualiza venda vinculada, se existir
        venda = getattr(lote, 'reg_venda', None)
        if venda:
            venda.tipo_venda = 'CANCELADA'
            venda.save(update_fields=['tipo_venda'])

        messages.success(request, "Reserva cancelada com sucesso!")
        return redirect('lista-empreendimento')


@method_decorator(has_permission_decorator('cancelarReservado'), name='dispatch')
class CancelarReservaView(View):

    def post(self, request, reserva_uuid, *args, **kwargs):
        venda = get_object_or_404(RegisterVenda, uuid=reserva_uuid)

        lote = venda.lote

        # Atualiza lote
        lote.situacao = 'PRE-RESERVA'
        lote.save(update_fields=['situacao'])

        # Atualiza venda
        venda.is_ativo = False
        venda.tipo_venda = 'NAO_ACEITE'
        venda.aceite_proposta = None
        venda.save(update_fields=['is_ativo', 'tipo_venda', 'aceite_proposta'])

        messages.error(request, "Reserva não aceita!")

        return redirect('lista-empreendimento')


@method_decorator(has_permission_decorator('cancelarAceiteReservado'), name='dispatch')
class CancelarAceiteReservaView(View):

    def post(self, request, reserva_uuid, *args, **kwargs):
        venda = get_object_or_404(RegisterVenda, uuid=reserva_uuid)

        lote = venda.lote

        # Atualiza lote
        lote.situacao = 'PRE-RESERVA'
        lote.save(update_fields=['situacao'])

        # Atualiza venda
        venda.is_ativo = False
        venda.tipo_venda = 'NAO_ACEITE'
        venda.save(update_fields=['is_ativo', 'tipo_venda'])

        messages.error(request, "Reserva não aceita!")

        return redirect('lista-empreendimento')



from django.views import View
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.utils.decorators import method_decorator
from datetime import timedelta
from rolepermissions.decorators import has_permission_decorator

from ..forms import RegisterVendaForm
from empreendimentos.forms import LoteForm
from ..models import RegisterVenda
from empreendimentos.models import Lote

from core.utils import formatar_moeda

from decimal import Decimal



@method_decorator(has_permission_decorator('criarVenda'), name='dispatch')
class CriarVendaView(UpdateView):

    model = RegisterVenda
    fields = []  # não precisa de formulário
    slug_field = 'uuid'
    slug_url_kwarg = 'venda_uuid'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        venda = self.object
        lote = venda.lote
        empreendimento = lote.quadra.empr

        # 🔥 Atualiza dados da venda
        venda.dt_venda = timezone.now()
        venda.tipo_venda = 'VENDIDO'

        # 🔥 Atualiza lote
        lote.situacao = 'VENDIDO'

        # 💾 Salva
        lote.save(update_fields=['situacao'])
        venda.save(update_fields=['dt_venda', 'tipo_venda'])

        messages.success(request, "Venda realizada com sucesso!")

        return redirect('listar-quadras', empreendimento_uuid=empreendimento.uuid)

@method_decorator(
    [has_permission_decorator('criarReservado'), transaction.atomic],
    name='dispatch'
)
class CriarReservadoView(UpdateView):

    model = RegisterVenda

    form_class = RegisterVendaForm

    template_name = "reserva.html"

    context_object_name = "form"

    # =====================================================
    # LOCK LOTE
    # =====================================================

    @transaction.atomic
    def dispatch(self, request, *args, **kwargs):

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    # =====================================================
    # LOTE
    # =====================================================

    def get_lote(self):

        return (

            Lote.objects

            .select_for_update()

            .select_related(
                'quadra__empr'
            )

            .get(
                uuid=self.kwargs.get(
                    'reserva_uuid'
                )
            )

        )

    # =====================================================
    # OBJECT
    # =====================================================

    def get_object(self, queryset=None):

        self.lote = self.get_lote()

        return getattr(
            self.lote,
            'reg_venda',
            None
        )

    # =====================================================
    # FORM KWARGS
    # =====================================================

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs.update({

            'user': self.request.user,

            'empreendimento': (
                self.lote.quadra.empr
            ),

            'lote': self.lote

        })

        return kwargs

    # =====================================================
    # HELPERS
    # =====================================================

    def calcular_valor_total(self, lote):

        try:

            return (

                float(lote.area or 0)

                *

                float(
                    lote.valor_metro_quadrado or 0
                )

            )

        except (
            TypeError,
            ValueError
        ):

            return 0

    def calcular_parcelas(
        self,
        valor_total,
        empreendimento
    ):

        try:

            total = int(
                empreendimento.quantidade_parcela or 0
            )

        except (
            TypeError,
            ValueError
        ):

            total = 0

        valor_parcela = (

            valor_total / total

            if total > 0 else 0

        )

        return (
            total,
            valor_parcela
        )

    # =====================================================
    # CONTEXTO
    # =====================================================

    def get_context_data(self, **kwargs):

        context = super().get_context_data(
            **kwargs
        )

        lote = self.lote

        empreendimento = lote.quadra.empr

        valor_total = (
            self.calcular_valor_total(
                lote
            )
        )

        (
            total_parcelas,
            valor_parcela

        ) = self.calcular_parcelas(
            valor_total,
            empreendimento
        )

        context.update({

            'lote': lote,

            'valor_formatado': (
                formatar_moeda(
                    valor_total
                )
            ),

            'valor_parcela_formatado': (
                formatar_moeda(
                    valor_parcela
                )
            ),

            'total_parcelas': (
                total_parcelas
            ),

        })

        return context

    # =====================================================
    # GET
    # =====================================================

    def get(self, request, *args, **kwargs):

        self.object = self.get_object()

        lote = self.lote

        reserva_existente = self.object

        # =================================================
        # PRÉ RESERVA
        # =================================================

        if not reserva_existente:

            if lote.situacao == "EM_RESERVA":

                lote.situacao = (
                    "PRE-RESERVA"
                )

            lote.tempo_reservado = (
                timezone.now().time()
            )

            lote.save(
                update_fields=[
                    'situacao',
                    'tempo_reservado'
                ]
            )

        return super().get(
            request,
            *args,
            **kwargs
        )

    # =====================================================
    # FORM VALID
    # =====================================================

    def form_valid(self, form):

        lote = self.lote

        empreendimento = (
            lote.quadra.empr
        )

        reserva_existente = (
            self.object
        )

        # =================================================
        # BLOQUEIO
        # =================================================

        if (

            reserva_existente

            and

            reserva_existente.tipo_venda not in ['CANCELADA', 'NAO_ACEITE']

        ):

            messages.error(

                self.request,

                (
                    'Já existe uma '
                    'venda ativa '
                    'para este lote.'
                )

            )

            return redirect(

                'listar-quadras',

                empreendimento_uuid=(
                    empreendimento.uuid
                )

            )

        # =================================================
        # INSTÂNCIA
        # =================================================

        reserva = form.save(
            commit=False
        )

        # =================================================
        # LOTE
        # =================================================

        reserva.lote = lote

        # =================================================
        # USER
        # =================================================

        reserva.user = (

            form.cleaned_data.get(
                'corretor'
            )

            if (
                self.request.user.tipo_usuario
                ==
                'ADMINISTRADOR'
            )

            else self.request.user

        )

        # =================================================
        # DESCONTO
        # =================================================

        desconto = (
            form.cleaned_data.get(
                'valor_desconto'
            )
            or Decimal('0.00')
        )

        # =================================================
        # TIPO VENDA
        # =================================================

        #if desconto > Decimal('0.00'):

        reserva.tipo_venda = (
              'ANALISE'
        )

        lote.situacao = (
            'ANALISE'
        )

        mensagem = (
            'Reserva enviada '
            'para análise.'
        )

        """else:

            reserva.tipo_venda = (
                'RESERVADO'
            )

            lote.situacao = (
                'RESERVADO'
            )

            mensagem = (
                'Reserva realizada '
                'com sucesso!'
            )"""

        # =================================================
        # STATUS
        # =================================================

        reserva.is_ativo = False

        reserva.dt_reserva = (

            timezone.now()

            +

            timedelta(
                days=empreendimento.tempo_reserva
            )

        )

        # =================================================
        # SAVE RESERVA
        # =================================================

        reserva.save()

        # =================================================
        # SAVE LOTE
        # =================================================

        lote.save(
            update_fields=['situacao']
        )

        # =================================================
        # SUCCESS
        # =================================================

        messages.success(
            self.request,
            mensagem
        )

        return redirect(

            'listar-quadras',

            empreendimento_uuid=(
                empreendimento.uuid
            )

        )

    # =====================================================
    # FORM INVALID
    # =====================================================

    def form_invalid(self, form):

        messages.error(

            self.request,

            (
                'Erro ao registrar '
                'reserva.'
            )

        )

        return super().form_invalid(
            form
        )

@method_decorator(transaction.atomic, name='dispatch')
class ReservaTemporariaView(UpdateView):

    model = Lote
    form_class = LoteForm
    template_name = 'reserva-temporaria-vendas.html'
    context_object_name = 'lote'
    slug_field = 'uuid'
    slug_url_kwarg = 'lote_uuid'

    print(context_object_name)


    # 🔒 LOCK + SELECT RELATED
    def get_queryset(self):
        return (
            Lote.objects
            .select_for_update()
            .select_related('quadra__empr')
        )

    # ======================
    # CONTEXTO (CÁLCULOS)
    # ======================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lote = self.object
        empreendimento = lote.quadra.empr

        # 💰 Cálculo valor total
        try:
            area = float(lote.area or 0)
            valor_metro = float(lote.valor_metro_quadrado or 0)
            valor = area * valor_metro
        except (TypeError, ValueError):
            valor = 0

        valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # 📊 Parcelas
        try:
            total_parcelas = int(empreendimento.quantidade_parcela or 0)
        except (TypeError, ValueError):
            total_parcelas = 0

        valor_parcela = valor / total_parcelas if total_parcelas > 0 else 0
        valor_parcela_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        try:
            valor_desconto = float(empreendimento.desconto or 0)
            valor_com_desconto = valor - (valor * (valor_desconto / 100))
        except (TypeError, ValueError):
            valor_com_desconto = 0

        valor_avista_formatado = f"R$ {valor_com_desconto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


        context.update({
            'valor_formatado': valor_formatado,
            'valor_parcela_formatado': valor_parcela_formatado,
            'total_parcelas': total_parcelas,
            'total_avista': valor_avista_formatado,
        })

        return context

    # ======================
    # GET → RESERVA TEMPORÁRIA
    # ======================
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        lote = self.object

        # 🔁 Defesa
        if lote.situacao == "EM_RESERVA" and not lote.user:
            lote.tempo_reservado = None
            lote.save(update_fields=['tempo_reservado'])
            messages.error(request, "Pré-reserva cancelada automaticamente.")

        # 🚫 Bloqueio
        if lote.situacao != "DISPONIVEL":
            messages.warning(request, "Este lote já está em reserva ou indisponível.")
            return redirect('lotes_disponiveis')

        # 🔒 Reserva
        lote.situacao = "EM_RESERVA"
        lote.tempo_reservado = timezone.now()
        lote.save(update_fields=['situacao', 'tempo_reservado'])

        return super().get(request, *args, **kwargs)

    # ======================
    # POST → PRÉ-RESERVA
    # ======================
    def form_valid(self, form):

        lote = form.save(commit=False)
        empreendimento = lote.quadra.empr

        lote.situacao = 'PRE-RESERVA'
        lote.data_termina_reserva = timezone.now() + timedelta(
            days=empreendimento.tempo_reserva
        )

        lote.user = self.request.user.first_name
        lote.telefone_user = self.request.user.contato

        lote.save()

        messages.success(self.request, "Pré-reserva salva com sucesso!")

        return redirect('listar-quadras', empreendimento_uuid=empreendimento.uuid)

    def form_invalid(self, form):
        messages.error(self.request, "Erro ao salvar pré-reserva.")
        return super().form_invalid(form)

@method_decorator(has_permission_decorator('renovarReserva'), name='dispatch')
class RenovaReservaView(View):

    def post(self, request, venda_uuid, *args, **kwargs):
        venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)
        empreendimento = venda.lote.quadra.empr

        venda.dt_reserva = timezone.now() + timedelta(
            days=empreendimento.tempo_reserva
        )
        venda.save(update_fields=['dt_reserva'])

        messages.success(request, "Reserva renovada com sucesso!")

        return redirect('listar-quadras', uuid=empreendimento.uuid)

@method_decorator(has_permission_decorator('renovarReserva'), name='dispatch')
class RenovaReservaView(View):

    def post(self, request, venda_uuid, *args, **kwargs):
        venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)

        empreendimento = venda.lote.quadra.empr

        # 🔥 Atualiza data da reserva
        venda.dt_reserva = timezone.now() + timedelta(
            days=empreendimento.tempo_reserva
        )

        venda.save(update_fields=['dt_reserva'])

        messages.success(request, "Reserva renovada com sucesso!")

        return redirect('listar-quadras', empreendimento_uuid=empreendimento.uuid)


@method_decorator(has_permission_decorator('aceitaReserva'), name='dispatch')
class AceitaReservaView(View):

    def post(self, request, reserva_uuid, *args, **kwargs):
        venda = get_object_or_404(RegisterVenda, uuid=reserva_uuid)

        lote = venda.lote

        # 🔥 Atualiza lote
        lote.situacao = 'RESERVADO'
        lote.save(update_fields=['situacao'])

        # 🔥 Atualiza venda
        venda.is_ativo = False
        venda.tipo_venda = 'RESERVADO'
        venda.save(update_fields=['is_ativo', 'tipo_venda'])

        messages.success(request, "Reserva aceita com sucesso!")

        return redirect('lista-empreendimento')
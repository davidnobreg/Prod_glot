from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max
from django.utils.timezone import now
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.decorators import method_decorator
from django.http import Http404

from rolepermissions.decorators import has_permission_decorator

from empreendimentos.models import Lote
from vendas.models import RegisterVenda, VendaDocumento
from vendas.services import checklist_documentos_cliente, documento_gerado_mais_recente
from clientes.models import ClienteTelefone, ClienteDocumento
from documentos.models import (
	DocumentoGerado,
	ModeloDocumento,
	StatusDocumento,
	TipoDocumento,
)
from documentos.views_gerar import _tipos_disponiveis
from vendas.views.create_views import _documento_assinado_com_lastro

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

        empreendimento = getattr(
            getattr(getattr(venda, 'lote', None), 'quadra', None),
            'empr', None
        )

        _tipos_ok = _tipos_disponiveis(self.request.user, venda)

        modelos_por_tipo = {}
        if empreendimento:
            for tipo in TipoDocumento:
                if tipo.value not in _tipos_ok:
                    continue
                modelos = ModeloDocumento.objects.para_empreendimento(
                    empreendimento, tipo=tipo.value
                )
                if modelos.exists():
                    padrao = ModeloDocumento.objects.padrao_para(
                        empreendimento, tipo.value
                    )
                    modelos_por_tipo[tipo.value] = {
                        'label': tipo.label,
                        'modelos': list(modelos.values('id', 'titulo', 'versao')),
                        'padrao_id': padrao.pk if padrao else None,
                    }

        docs_existentes = (
            DocumentoGerado.objects.filter(venda=venda, modelo__tipo__in=_tipos_ok)
            .exclude(status=StatusDocumento.CANCELADO)
            .order_by('-criado_em')
            if venda else DocumentoGerado.objects.none()
        )

        from clientes.models import ClienteDocumento
        documentos_cliente = (
            ClienteDocumento.objects.filter(
                cliente=venda.cliente,
                status='disponivel',
            )
            if venda and venda.cliente
            else ClienteDocumento.objects.none()
        )

        context.update({
            'valor_lote': valor_lote,
            'lote': lote,
            'reservas': venda,
            'contatoCliente': cliente_contato,
            'modelos_por_tipo': modelos_por_tipo,
            'docs_existentes': docs_existentes,
            'documentos_cliente': documentos_cliente,
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


            _user = reserva_publica.user if reserva_publica else None
            context = {
                'contatoNome': _user.first_name if _user else '',
                'contatoCorretor': _user.contato if _user else None,
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

        venda = kwargs.get('reservas')
        empreendimento = getattr(
            getattr(getattr(venda, 'lote', None), 'quadra', None),
            'empr', None
        )

        _tipos_ok = _tipos_disponiveis(
            self.request.user,
            venda,
        )

        modelos_por_tipo = {}
        if empreendimento:
            for tipo in TipoDocumento:
                if tipo.value not in _tipos_ok:
                    continue
                modelos = ModeloDocumento.objects.para_empreendimento(
                    empreendimento, tipo=tipo.value
                )
                if modelos.exists():
                    padrao = ModeloDocumento.objects.padrao_para(
                        empreendimento, tipo.value
                    )
                    modelos_por_tipo[tipo.value] = {
                        'label': tipo.label,
                        'modelos': list(modelos.values('id', 'titulo', 'versao')),
                        'padrao_id': padrao.pk if padrao else None,
                    }

        docs_existentes = DocumentoGerado.objects.filter(
            venda=venda, modelo__tipo__in=_tipos_ok,
        ).exclude(status=StatusDocumento.CANCELADO).order_by('-criado_em') if venda else DocumentoGerado.objects.none()

        proposta_disponivel = (
            docs_existentes.filter(modelo__tipo='proposta', status='disponivel').first()
            if venda else None
        )

        context['contatoCliente'] = (
            ClienteTelefone.objects.filter(cliente=venda.cliente).first()
            if venda and venda.cliente else None
        )
        context['proposta_aprovada'] = (
            VendaDocumento.objects.filter(
                venda=venda,
                tipo='proposta_assinada',
                status='aprovado',
            ).exists()
            if venda else False
        )
        proposta_com_lastro = (
            _documento_assinado_com_lastro(venda, 'proposta_assinada') if venda else False
        )
        contrato_com_lastro = (
            _documento_assinado_com_lastro(venda, 'contrato_assinado') if venda else False
        )
        context['proposta_com_lastro'] = proposta_com_lastro
        context['contrato_com_lastro'] = contrato_com_lastro
        context['pre_venda_liberada'] = proposta_com_lastro and contrato_com_lastro
        context['modelos_por_tipo'] = modelos_por_tipo
        context['docs_existentes'] = docs_existentes
        context['proposta_disponivel'] = proposta_disponivel
        context['venda_documentos'] = (
            VendaDocumento.objects.filter(venda=venda)
            .vigentes()
            .select_related('enviado_por', 'aprovado_por', 'documento_gerado')
            if venda else VendaDocumento.objects.none()
        )

        ciclos_historico = (
            VendaDocumento.objects.filter(venda=venda, status='arquivado')
            .values('ciclo')
            .distinct()
            .order_by('-ciclo')
            if venda else []
        )
        context['historico_por_ciclo'] = [
            {
                'ciclo': c['ciclo'],
                'docs': VendaDocumento.objects.filter(
                    venda=venda, status='arquivado', ciclo=c['ciclo']
                ).select_related('enviado_por').order_by('-enviado_em')
            }
            for c in ciclos_historico
        ]

        return context


class PreVendaDetalheView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        if getattr(request.user, 'tipo_usuario', None) != 'ADMINISTRADOR':
            messages.error(request, "Acesso não permitido.")
            return redirect('lista-empreendimento')

        venda = get_object_or_404(
            RegisterVenda.objects.select_related(
                'cliente', 'lote__quadra__empr', 'corretor'
            ),
            uuid=kwargs.get('venda_uuid')
        )
        cliente = venda.cliente

        checklist_cliente = checklist_documentos_cliente(cliente)

        docs_venda = VendaDocumento.objects.filter(venda=venda).vigentes()

        proposta_aprovada = docs_venda.filter(tipo='proposta_assinada', status='aprovado').first()
        contrato_aprovado = docs_venda.filter(tipo='contrato_assinado', status='aprovado').first()

        context = {
            'venda': venda,
            'checklist_cliente': checklist_cliente,
            'proposta_aprovada': proposta_aprovada,
            'contrato_aprovado': contrato_aprovado,
        }
        return render(request, 'vendas/pre_venda_detalhe.html', context)


class VendaDocumentoUploadView(LoginRequiredMixin, View):

    def post(self, request, venda_uuid):
        venda = get_object_or_404(RegisterVenda, uuid=venda_uuid)

        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        if tipo_usuario not in ('CORRETOR', 'ADMINISTRADOR'):
            raise Http404
        if tipo_usuario == 'CORRETOR' and venda.corretor != request.user:
            raise Http404

        arquivo = request.FILES.get('arquivo_assinado')
        if not arquivo:
            messages.error(request, 'Arquivo obrigatório.')
            return redirect('reservadoDetalhes', reserva_uuid=venda.lote.uuid)

        ciclo_atual = (
            VendaDocumento.objects.filter(venda=venda)
            .vigentes()
            .aggregate(Max('ciclo'))['ciclo__max'] or 1
        )

        tipo = request.POST.get('tipo', 'outros')
        documento_gerado = documento_gerado_mais_recente(venda, tipo)

        VendaDocumento.objects.create(
            venda=venda,
            ciclo=ciclo_atual,
            tipo=tipo,
            arquivo_assinado=arquivo,
            observacao=request.POST.get('observacao', ''),
            enviado_por=request.user,
            documento_gerado=documento_gerado,
        )
        messages.success(request, 'Documento enviado com sucesso.')
        return redirect('reservadoDetalhes', reserva_uuid=venda.lote.uuid)


class VendaDocumentoAprovarView(LoginRequiredMixin, View):

    def post(self, request, pk):
        if getattr(request.user, 'tipo_usuario', None) != 'ADMINISTRADOR':
            raise Http404

        doc = get_object_or_404(VendaDocumento, pk=pk)

        with transaction.atomic():
            VendaDocumento.objects.filter(
                venda=doc.venda, tipo=doc.tipo, status='aprovado',
            ).exclude(pk=doc.pk).update(status='arquivado')

            doc.status = 'aprovado'
            doc.aprovado_por = request.user
            doc.aprovado_em = now()
            doc.save(update_fields=['status', 'aprovado_por', 'aprovado_em'])

        messages.success(request, 'Documento aprovado.')
        return redirect('reservadoDetalhes', reserva_uuid=doc.venda.lote.uuid)


class VendaDocumentoRejeitarView(LoginRequiredMixin, View):

    def post(self, request, pk):
        if getattr(request.user, 'tipo_usuario', None) != 'ADMINISTRADOR':
            raise Http404

        doc = get_object_or_404(VendaDocumento, pk=pk)
        doc.status = 'rejeitado'
        doc.save(update_fields=['status'])

        messages.success(request, 'Documento rejeitado.')
        return redirect('reservadoDetalhes', reserva_uuid=doc.venda.lote.uuid)

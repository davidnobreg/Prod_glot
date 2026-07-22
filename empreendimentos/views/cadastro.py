from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from rolepermissions.decorators import has_permission_decorator

from django.db import transaction

from base.models import Endereco

from ..forms import (EmpreendimentoForm, EnderecoForm, EmpreendimentoStep1Form,
                    EmpresaStep2Form, RepresentanteFormSet,
                    DocumentoEmpreendimentoForm, DocumentoRepresentanteForm,
                    ConfiguracaoGatewayForm)
from ..models import Empreendimento, RepresentanteLegal, DocumentoRepresentante
from .. import services as empreendimento_services
from cobranca.models import ConfiguracaoGateway


@has_permission_decorator('criarEmpreendimento')
def criarEmpreendimento(request):
    if request.method == 'POST':
        form = EmpreendimentoForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Verifique os campos obrigatórios.")
            return render(request, 'empreendimento.html', {
                'form': form,
            })

        try:
            with transaction.atomic():
                form.save()
                messages.success(request, "Empreendimento criado com sucesso!")
                return redirect('lista-empreendimento-tabela')

        except Exception as e:
            messages.error(request, f"Erro ao criar empreendimento: {e}")

    # =========================
    # GET
    # =========================
    return render(request, 'empreendimento.html', {
        'form': EmpreendimentoForm(),
    })


# ===================================================================
# Wizard de cadastro de Empreendimento
# ===================================================================

_WIZARD_SESSION_KEY = 'wizard_empreendimento_uuid'

_WIZARD_STEPS = [
    ('Dados gerais', 'empreendimento_wizard_step1'),
    ('Empresa', 'empreendimento_wizard_step2'),
    ('Representantes', 'empreendimento_wizard_step3'),
    ('Configurações', 'empreendimento_wizard_step4'),
    ('Revisão', 'empreendimento_wizard_step5'),
]

CATEGORIAS_DOC_STEP1 = (
    'matricula_imovel', 'planta_loteamento', 'memorial_descritivo',
    'registro_loteamento', 'mapa', 'tabela', 'outro',
)
CATEGORIAS_DOC_STEP2 = ('contrato_social', 'procuracao', 'alvara', 'licenca_ambiental')


def _wizard_get_draft(request):
    """Retorna empreendimento rascunho (is_ativo=False) apontado pela
    sessão, ou None se não houver rascunho em andamento."""
    empreendimento_uuid = request.session.get(_WIZARD_SESSION_KEY)
    if not empreendimento_uuid:
        return None
    return Empreendimento.objects.filter(uuid=empreendimento_uuid, is_ativo=False).first()


def _wizard_render(request, template, current_step, context):
    context['wizard_steps'] = _WIZARD_STEPS
    context['current_step'] = current_step
    return render(request, template, context)


def _deletar_wizard_draft(draft):
    """Apaga o draft de cadastro inteiro: documentos do empreendimento,
    representantes (com seus próprios endereços e documentos), os 2
    endereços do empreendimento, o logo e o registro em si. Arquivo
    sempre apagado do storage antes do registro (mesmo cuidado de
    `services.remover_documento_*`), senão o arquivo fica órfão no B2
    mesmo depois do CASCADE apagar a linha do banco."""
    for documento in draft.documentos.all():
        documento.arquivo.delete(save=False)
        documento.delete()

    for representante in draft.representantes.all():
        for documento in representante.documentos.all():
            documento.arquivo.delete(save=False)
            documento.delete()
        endereco_id = representante.endereco_id
        representante.delete()
        if endereco_id:
            Endereco.objects.filter(pk=endereco_id).delete()

    if draft.logo:
        draft.logo.delete(save=False)

    if draft.endereco_empresa_id:
        Endereco.objects.filter(pk=draft.endereco_empresa_id).delete()
    if draft.endereco_empreendimento_id:
        Endereco.objects.filter(pk=draft.endereco_empreendimento_id).delete()

    draft.delete()


@has_permission_decorator('criarEmpreendimento')
@require_POST
def wizard_cancelar(request):
    """Cancela o cadastro em andamento — apaga o draft (+ endereços,
    representantes, documentos e arquivos do storage) e limpa a
    sessão. Antes disso, o botão Cancelar só redirecionava pra listagem
    sem limpar nada, abandonando o draft is_ativo=False (e tudo vinculado
    a ele) permanentemente no banco."""
    draft = _wizard_get_draft(request)
    if draft is not None:
        with transaction.atomic():
            _deletar_wizard_draft(draft)
    request.session.pop(_WIZARD_SESSION_KEY, None)
    return redirect('lista-empreendimento-tabela')


def _doc_form_filtrado(categorias, prefix=None):
    """DocumentoEmpreendimentoForm com o select de categoria restrito às
    categorias relevantes do step atual (evita listar categoria de
    contrato social no step de dados gerais do loteamento, e vice-versa).

    `prefix` evita colisão de `name` quando este form é renderizado dentro
    do mesmo <form> que já tem um campo 'nome' próprio (caso do step1, que
    reúne dados gerais + documentos num único <form>)."""
    doc_form = DocumentoEmpreendimentoForm(prefix=prefix)
    doc_form.fields['categoria'].choices = [
        c for c in doc_form.fields['categoria'].choices if c[0] in categorias
    ]
    return doc_form


@has_permission_decorator('criarEmpreendimento')
def wizard_step1(request):
    """Step 1 — dados gerais + endereço do loteamento + documentos gerais.
    Cria o rascunho (is_ativo=False) no POST."""
    draft = _wizard_get_draft(request)

    if request.method == 'POST':
        era_draft_novo = draft is None
        form = EmpreendimentoStep1Form(request.POST, request.FILES, instance=draft)
        form_endereco = EnderecoForm(
            request.POST, prefix='empreendimento',
            instance=draft.endereco_empreendimento if draft else None,
        )
        if form.is_valid() and form_endereco.is_valid():
            with transaction.atomic():
                empreendimento = form.save(commit=False)
                empreendimento.is_ativo = False
                if empreendimento.tempo_reserva is None:
                    empreendimento.tempo_reserva = 0
                if empreendimento.quantidade_parcela is None:
                    empreendimento.quantidade_parcela = 0
                empreendimento.endereco_empreendimento = empreendimento_services.criar_ou_atualizar_endereco(
                    form_endereco.cleaned_data,
                    endereco=draft.endereco_empreendimento if draft else None,
                )
                empreendimento.save()
            request.session[_WIZARD_SESSION_KEY] = str(empreendimento.uuid)

            if era_draft_novo:
                # Primeiro salvamento: fica no step1 (agora com draft já
                # existente) pra liberar o widget de documentos do
                # loteamento, que depende de um Empreendimento salvo (FK).
                # Sem isso o usuário precisava ir pro step2 e voltar pro
                # step1 só pra conseguir anexar documento.
                messages.success(request, 'Dados salvos. Anexe os documentos do loteamento (opcional) e clique em Próximo novamente para continuar.')
                documentos = empreendimento.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP1)
                return _wizard_render(request, 'wizard/step1_dados_gerais.html', 1, {
                    'form': EmpreendimentoStep1Form(instance=empreendimento),
                    'form_endereco': EnderecoForm(prefix='empreendimento', instance=empreendimento.endereco_empreendimento),
                    'documentos': documentos,
                    'doc_form': _doc_form_filtrado(CATEGORIAS_DOC_STEP1, prefix='doclote'),
                })

            return redirect('empreendimento_wizard_step2')

        messages.error(request, 'Verifique os campos obrigatórios.')
        documentos = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP1) if draft else []
        return _wizard_render(request, 'wizard/step1_dados_gerais.html', 1, {
            'form': form,
            'form_endereco': form_endereco,
            'documentos': documentos,
            'doc_form': _doc_form_filtrado(CATEGORIAS_DOC_STEP1, prefix='doclote'),
        })

    form = EmpreendimentoStep1Form(instance=draft)
    form_endereco = EnderecoForm(
        prefix='empreendimento',
        instance=draft.endereco_empreendimento if draft else None,
    )
    documentos = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP1) if draft else []
    return _wizard_render(request, 'wizard/step1_dados_gerais.html', 1, {
        'form': form,
        'form_endereco': form_endereco,
        'documentos': documentos,
        'doc_form': _doc_form_filtrado(CATEGORIAS_DOC_STEP1, prefix='doclote'),
    })


@has_permission_decorator('criarEmpreendimento')
def wizard_step2(request):
    """Step 2 — empresa + endereço da empresa (obrigatório, próprio)."""
    draft = _wizard_get_draft(request)
    if draft is None:
        messages.error(request, 'Inicie o cadastro pelo passo 1.')
        return redirect('empreendimento_wizard_step1')

    if request.method == 'POST':
        form = EmpresaStep2Form(request.POST, instance=draft)
        form_endereco = EnderecoForm(request.POST, prefix='empresa', instance=draft.endereco_empresa)

        if form.is_valid() and form_endereco.is_valid():
            with transaction.atomic():
                empreendimento = form.save(commit=False)
                empreendimento.endereco_empresa = empreendimento_services.criar_ou_atualizar_endereco(
                    form_endereco.cleaned_data, endereco=draft.endereco_empresa
                )
                empreendimento.save()
            return redirect('empreendimento_wizard_step3')

        messages.error(request, 'Verifique os campos obrigatórios.')
        documentos = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP2)
        return _wizard_render(request, 'wizard/step2_empresa.html', 2, {
            'form': form, 'form_endereco': form_endereco,
            'documentos': documentos, 'doc_form': _doc_form_filtrado(CATEGORIAS_DOC_STEP2),
        })

    form = EmpresaStep2Form(instance=draft)
    form_endereco = EnderecoForm(prefix='empresa', instance=draft.endereco_empresa)
    documentos = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP2)
    return _wizard_render(request, 'wizard/step2_empresa.html', 2, {
        'form': form, 'form_endereco': form_endereco,
        'documentos': documentos, 'doc_form': _doc_form_filtrado(CATEGORIAS_DOC_STEP2),
    })


@has_permission_decorator('criarEmpreendimento')
def wizard_step3(request):
    """Step 3 — representantes legais (sócio/administrador), mínimo 1,
    cada um com seu próprio endereço."""
    draft = _wizard_get_draft(request)
    if draft is None:
        messages.error(request, 'Inicie o cadastro pelo passo 1.')
        return redirect('empreendimento_wizard_step1')

    queryset = RepresentanteLegal.objects.filter(empreendimento=draft, is_ativo=True).order_by('id')

    if request.method == 'POST':
        formset = RepresentanteFormSet(request.POST, queryset=queryset, prefix='representante')
        enderecos_forms = [
            EnderecoForm(request.POST, prefix=f'representante-{i}-endereco')
            for i in range(len(formset.forms))
        ]

        if formset.is_valid() and all(f.is_valid() for f in enderecos_forms):
            algum_novo = False
            try:
                with transaction.atomic():
                    for form, form_endereco in zip(formset.forms, enderecos_forms):
                        if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                            continue
                        representante = form.instance
                        dados = {k: v for k, v in form.cleaned_data.items() if k != 'id'}
                        if representante.pk:
                            empreendimento_services.atualizar_representante(
                                representante, dados, endereco_dados=form_endereco.cleaned_data
                            )
                        else:
                            # Formset tem min_num=1 e todos os campos opcionais —
                            # se o usuário clicar em Próximo sem preencher nada
                            # (nem representante nem endereço), não cria registro
                            # vazio só pra existir. Cadastro parcial continua
                            # permitido: basta 1 campo preenchido em qualquer um
                            # dos dois formulários.
                            representante_vazio = not any(v not in (None, '') for v in dados.values())
                            endereco_vazio = not any(v not in (None, '') for v in form_endereco.cleaned_data.values())
                            if representante_vazio and endereco_vazio:
                                continue
                            algum_novo = True
                            empreendimento_services.criar_representante(
                                draft, dados, endereco_dados=form_endereco.cleaned_data
                            )
            except ValidationError as exc:
                # full_clean() do RepresentanteLegal (services.criar_representante/
                # atualizar_representante) pode rejeitar dados válidos pro form mas
                # inválidos pro model (ex: CPF duplicado no mesmo empreendimento).
                # Sem isso, a ValidationError subia crua e virava 500 — o
                # transaction.atomic() já desfez qualquer save parcial deste POST
                # antes de re-lançar, então nada fica inconsistente no banco.
                messages.error(
                    request,
                    '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
                )
                docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
                reps_docs = [
                    form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
                    for form in formset.forms
                ]
                return _wizard_render(request, 'wizard/step3_representantes.html', 3, {
                    'formset': formset, 'enderecos_forms': enderecos_forms,
                    'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
                    'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
                    'empty_doc_form': DocumentoRepresentanteForm(),
                })

            if algum_novo:
                # Representante recém-criado só ganha o widget de
                # documentos depois de ter pk salvo — fica no step3 (com
                # formset reconstruído do banco) em vez de já avançar pro
                # step4, senão o usuário precisaria ir pro step4 e voltar
                # só pra conseguir anexar documento do representante.
                messages.success(request, 'Representantes salvos. Anexe os documentos (opcional) e clique em Próximo novamente para continuar.')
                queryset = RepresentanteLegal.objects.filter(empreendimento=draft, is_ativo=True).order_by('id')
                formset = RepresentanteFormSet(queryset=queryset, prefix='representante')
                enderecos_forms = [
                    EnderecoForm(prefix=f'representante-{i}-endereco', instance=form.instance.endereco if form.instance.pk else None)
                    for i, form in enumerate(formset.forms)
                ]
                docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
                reps_docs = [
                    form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
                    for form in formset.forms
                ]
                return _wizard_render(request, 'wizard/step3_representantes.html', 3, {
                    'formset': formset, 'enderecos_forms': enderecos_forms,
                    'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
                    'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
                    'empty_doc_form': DocumentoRepresentanteForm(),
                })

            return redirect('empreendimento_wizard_step4')

        messages.error(request, 'Verifique os campos obrigatórios dos representantes.')
        docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
        reps_docs = [
            form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
            for form in formset.forms
        ]
        return _wizard_render(request, 'wizard/step3_representantes.html', 3, {
            'formset': formset, 'enderecos_forms': enderecos_forms,
            'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
            'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
            'empty_doc_form': DocumentoRepresentanteForm(),
        })

    formset = RepresentanteFormSet(queryset=queryset, prefix='representante')
    enderecos_forms = [
        EnderecoForm(prefix=f'representante-{i}-endereco', instance=form.instance.endereco if form.instance.pk else None)
        for i, form in enumerate(formset.forms)
    ]
    docs_forms = [DocumentoRepresentanteForm() for _ in formset.forms]
    reps_docs = [
        form.instance.documentos.all() if form.instance.pk else DocumentoRepresentante.objects.none()
        for form in formset.forms
    ]
    return _wizard_render(request, 'wizard/step3_representantes.html', 3, {
        'formset': formset, 'enderecos_forms': enderecos_forms,
        'reps_com_endereco': zip(formset.forms, enderecos_forms, reps_docs, docs_forms),
        'empty_endereco_form': EnderecoForm(prefix='representante-__prefix__-endereco'),
        'empty_doc_form': DocumentoRepresentanteForm(),
    })


@has_permission_decorator('criarEmpreendimento')
def wizard_step4(request):
    """Step 4 — configurações (reserva, parcelas, desconto, correção)."""
    draft = _wizard_get_draft(request)
    if draft is None:
        messages.error(request, 'Inicie o cadastro pelo passo 1.')
        return redirect('empreendimento_wizard_step1')

    campos = ('tempo_reserva', 'quantidade_parcela', 'desconto', 'tipo_correcao')
    campos_inteiros = ('tempo_reserva', 'quantidade_parcela')

    if request.method == 'POST':
        for campo in campos:
            if campo in request.POST:
                valor = request.POST.get(campo)
                if campo in campos_inteiros and valor == '':
                    valor = None
                setattr(draft, campo, valor)

        gateway_instance = getattr(draft, 'configuracao_gateway', None)
        gateway_form = ConfiguracaoGatewayForm(request.POST, prefix='gateway', instance=gateway_instance)

        try:
            draft.full_clean(validate_unique=False)
            draft.save(update_fields=campos)
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages) if hasattr(e, 'messages') else str(e))
            return _wizard_render(request, 'wizard/step4_configuracoes.html', 4, {
                'empreendimento': draft, 'gateway_form': gateway_form,
            })

        if gateway_form.is_valid():
            dados = gateway_form.dados_preenchidos()
            if dados:
                ConfiguracaoGateway.objects.update_or_create(empreendimento=draft, defaults=dados)

        return redirect('empreendimento_wizard_step5')

    gateway_instance = getattr(draft, 'configuracao_gateway', None)
    return _wizard_render(request, 'wizard/step4_configuracoes.html', 4, {
        'empreendimento': draft,
        'gateway_form': ConfiguracaoGatewayForm(prefix='gateway', instance=gateway_instance),
    })


@has_permission_decorator('criarEmpreendimento')
def wizard_step5(request):
    """Step 5 — revisão de tudo + commit final: ativa o empreendimento."""
    draft = _wizard_get_draft(request)
    if draft is None:
        messages.error(request, 'Inicie o cadastro pelo passo 1.')
        return redirect('empreendimento_wizard_step1')

    if request.method == 'POST':
        with transaction.atomic():
            draft.is_ativo = True
            draft.save(update_fields=['is_ativo'])

        request.session.pop(_WIZARD_SESSION_KEY, None)
        messages.success(request, 'Empreendimento cadastrado com sucesso!')
        return redirect('lista-empreendimento-tabela')

    representantes = draft.representantes.filter(is_ativo=True).prefetch_related('documentos')
    documentos_gerais = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP1)
    documentos_empresa = draft.documentos.filter(categoria__in=CATEGORIAS_DOC_STEP2)

    return _wizard_render(request, 'wizard/step5_revisao.html', 5, {
        'draft': draft,
        'representantes': representantes,
        'documentos_gerais': documentos_gerais,
        'documentos_empresa': documentos_empresa,
    })

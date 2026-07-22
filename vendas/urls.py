from django.urls import path
from .views.create_views import (
    AceitaReservaView,
    CriarReservadoView,
    CriarVendaView,
    EfetivarVendaView,
    ReservaTemporariaView,
    RenovaReservaView
)
from .views.delete_views import (
    CancelarVendaView,
    CancelarReservadoCadastroView,
    CancelarReservaView,
    CancelarAceiteReservaView,
    CancelarPreVendaView,

)
from .views.detail_views import (
    AnaliseView,
    ReservadoView,
    ReservadoDetalheView,
    PreVendaDetalheView,
    VendaDocumentoUploadView,
    VendaDocumentoAprovarView,
    VendaDocumentoRejeitarView,
)
from .views.transferencia_views import (
    IniciarTransferenciaView,
    DetalheTransferenciaView,
    EfetivarTransferenciaView,
    CancelarTransferenciaView,
    UploadTermoAssinadoView,
    UploadCertidaoIptuView,
)
from .views.distrato_views import (
    IniciarDistratoView,
    IniciarDistratoAdministrativoView,
    DetalheDistratoView,
    AvancarParaAssinaturaView,
    UploadTermoDistratoView,
    ConcluirDistratoView,
    CancelarDistratoView,
)
from .views.list_views import (
    ListasAnalisesView,
    ListarendaRelatorioView,
    ListaVendaView,
    RelatorioReservaView

)

urlpatterns = [
    path('aceita_analise/<uuid:reserva_uuid>/', AceitaReservaView.as_view(), name='aceita-analise'),
    path('analise/<uuid:lote_uuid>/', AnaliseView.as_view(), name='analise'),
    path('insert_venda/<uuid:venda_uuid>/', CriarVendaView.as_view(), name='criar-venda'),  # 11
    path('insert_reserva/<uuid:reserva_uuid>/', CriarReservadoView.as_view(), name='reserva-create'),  # 1
    path('reservado/<uuid:lote_uuid>/', ReservadoView.as_view(), name='reservado'),  # 5
    path('reservado_detalhes/<uuid:reserva_uuid>/', ReservadoDetalheView.as_view(), name='reservadoDetalhes'),  # 9
    path('reserva_temporario/<uuid:lote_uuid>/', ReservaTemporariaView.as_view(), name='reserva_temporaria'),  # 7
    path('select/<uuid:venda_uuid>/', RenovaReservaView.as_view(), name='renova-reserva-select'),  # 10
    path('renova_reserva/<uuid:venda_uuid>/', RenovaReservaView.as_view(), name='renova-reserva'),  # 14

    path('listar_venda_relatorio/', ListarendaRelatorioView.as_view(), name='lista-venda-relatorio'),  # 2
    path('listar_reserva/', RelatorioReservaView.as_view(), name='lista-reserva'),
    path('listar_analise/', ListasAnalisesView.as_view(), name='lista-analise'),# 3
    path('listar_venda/', ListaVendaView.as_view(), name='lista-venda'),  # 4

    path('venda_delete/<uuid:delete_uuid>/', CancelarVendaView.as_view(), name='delete-venda'),  # 6
    path('reservado_cancelada_cadastro/<uuid:cancelaReserva_uuid>/', CancelarReservadoCadastroView.as_view(),
         name='cancelar-reservado-cadastro'),  # 8
    path('reservado_delete_lista/<uuid:reserva_uuid>/', CancelarReservaView.as_view(), name='delete-reservado-lista'),
    # 12
    path('reservado_delete/<uuid:reserva_uuid>/', CancelarReservaView.as_view(), name='delete-reservado'),
    path('reservado_delete_aceite/<uuid:reserva_uuid>/', CancelarAceiteReservaView.as_view(), name='delete-aceite'),# 13

    path('pre-venda/<uuid:venda_uuid>/', PreVendaDetalheView.as_view(), name='pre-venda-detalhe'),
    path('pre-venda/cancelar/<uuid:venda_uuid>/', CancelarPreVendaView.as_view(), name='cancelar-pre-venda'),
    path('efetivar-venda/<uuid:venda_uuid>/', EfetivarVendaView.as_view(), name='efetivar-venda'),
    path('venda/<uuid:venda_uuid>/documento/upload/', VendaDocumentoUploadView.as_view(), name='venda-documento-upload'),
    path('venda/documento/<uuid:doc_uuid>/aprovar/', VendaDocumentoAprovarView.as_view(), name='venda-documento-aprovar'),
    path('venda/documento/<uuid:doc_uuid>/rejeitar/', VendaDocumentoRejeitarView.as_view(), name='venda-documento-rejeitar'),

    path('transferencia/iniciar/<uuid:venda_uuid>/', IniciarTransferenciaView.as_view(), name='transferencia-iniciar'),
    path('transferencia/<uuid:transferencia_uuid>/', DetalheTransferenciaView.as_view(), name='transferencia-detalhe'),
    path('transferencia/<uuid:transferencia_uuid>/efetivar/', EfetivarTransferenciaView.as_view(), name='transferencia-efetivar'),
    path('transferencia/<uuid:transferencia_uuid>/cancelar/', CancelarTransferenciaView.as_view(), name='transferencia-cancelar'),
    path('transferencia/<uuid:transferencia_uuid>/upload-termo/', UploadTermoAssinadoView.as_view(), name='transferencia-upload-termo'),
    path('transferencia/<uuid:transferencia_uuid>/upload-certidao-iptu/', UploadCertidaoIptuView.as_view(), name='transferencia-upload-certidao-iptu'),

    path('distrato/iniciar/<uuid:venda_uuid>/', IniciarDistratoView.as_view(), name='iniciar-distrato'),
    path('distrato/administrativo/iniciar/<uuid:venda_uuid>/', IniciarDistratoAdministrativoView.as_view(), name='iniciar-distrato-administrativo'),
    path('distrato/<uuid:distrato_uuid>/', DetalheDistratoView.as_view(), name='distrato-detalhe'),
    path('distrato/<uuid:distrato_uuid>/aguardar-assinatura/', AvancarParaAssinaturaView.as_view(), name='distrato-aguardar-assinatura'),
    path('distrato/<uuid:distrato_uuid>/upload-termo/', UploadTermoDistratoView.as_view(), name='distrato-upload-termo'),
    path('distrato/<uuid:distrato_uuid>/concluir/', ConcluirDistratoView.as_view(), name='concluir-distrato'),
    path('distrato/<uuid:distrato_uuid>/cancelar/', CancelarDistratoView.as_view(), name='cancelar-distrato'),
]

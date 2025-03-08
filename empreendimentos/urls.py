from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import criar_Empreendimento, lista_Empreendimento, lista_Empreendimento_tabela, lista_Quadra, \
    delete_empreendimento, altera_empreendimento, select_empreendimento, \
    ImportarDadosView

urlpatterns = [
    # Cadastro de cliente
    path('insert_empreendimento/', criar_Empreendimento, name='criar-empreendimento'),

    path('select/<int:empreendimento_id>/', select_empreendimento, name='select-empreendimento'),

    path('alterar_empreendimento/<int:id>/', altera_empreendimento, name='alterar-empreendimento'),

    path('deletar_empreendimento/<int:id>', delete_empreendimento, name='deletar-empreendimento'),

    path('insert_arq/<int:id>/', ImportarDadosView.as_view(), name='arquivo'),

    path('', lista_Empreendimento, name='lista-empreendimento'),

    path('listar_empreendimento/', lista_Empreendimento_tabela, name='lista-empreendimento-tabela'),

    path('listar_quadras/<int:id>/', lista_Quadra, name='listar-quadras')

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # Adicionar Isto
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Adicionar Isto

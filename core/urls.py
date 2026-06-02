from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', include('accounts.urls'), name='accounts'),
    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls'), name='clientes'),
    path('dashboard/', include('dashboard.urls'), name='dashboard'),
    path('documentos/', include('documentos.urls'), name='documentos'),
    path('empreendimentos/', include('empreendimentos.urls'), name='empreendimentos'),
    # path('mensagem/', include('mensagem.urls'), name='message'),
    path('vendas/', include('vendas.urls'), name='vendas')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'base.views.not_found'
handler403 = 'base.views.handler403'
handler500 = 'base.views.handler500'
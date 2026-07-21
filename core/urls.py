from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve


urlpatterns = [
    path('', include('accounts.urls'), name='accounts'),
    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls'), name='clientes'),
    path('cobranca/', include('cobranca.urls'), name='cobranca'),
    path('dashboard/', include('dashboard.urls'), name='dashboard'),
    path('documentos/', include('documentos.urls'), name='documentos'),
    #path('documentos/', include('documentos.urls_documentos')),
    path('empreendimentos/', include('empreendimentos.urls'), name='empreendimentos'),
    # path('mensagem/', include('mensagem.urls'), name='message'),
    path('vendas/', include('vendas.urls'), name='vendas')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Produção sem nginx dedicado — Django serve media via gunicorn
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

handler404 = 'base.views.not_found'
handler403 = 'base.views.handler403'
handler500 = 'base.views.handler500'
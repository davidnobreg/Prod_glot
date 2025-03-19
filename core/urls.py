from django.contrib import admin
from django.urls import path, include  # adicionar include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls'), name='clientes'),
    path('empreendimentos/', include('empreendimentos.urls'), name='empreendimentos'),
    path('vendas/', include('vendas.urls'), name='vendas'),

    path('', include('accounts.urls'), name='accounts'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'base.views.not_found'
handler403 = 'base.views.handler403'

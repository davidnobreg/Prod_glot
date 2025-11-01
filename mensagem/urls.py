from django.urls import path
from .views import enviar_mensagem_view

urlpatterns = [
    path('enviar/', enviar_mensagem_view, name='enviar_mensagem'),
]

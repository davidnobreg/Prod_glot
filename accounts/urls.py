from django.urls import path, include
from django.contrib.auth import views as auth_view


from . import views

urlpatterns = [

    path('', auth_view.LoginView.as_view(template_name="login.html"), name='login'),

    path('cadastre-se/', views.register, name='criar-cadastro'),

    path('sair/', auth_view.LogoutView.as_view(next_page= 'login', http_method_names = ['get', 'post', 'options']), name='logout'),

    path('listar_usuarios/', views.listar, name='lista-usuario'),
]

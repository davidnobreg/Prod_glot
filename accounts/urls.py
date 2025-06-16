from django.urls import path, include
from django.contrib.auth import views as auth_view

from . import views

urlpatterns = [
    # path('', auth_view.LoginView.as_view(template_name="login.html"), name='login'),

    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    # path('sair/', auth_view.LogoutView.as_view(next_page='login', http_method_names=['get', 'post', 'options']),
    #  name='logout'),

    path('cadastrar/', views.criarUsuario, name='criar-cadastro'),

    path('listar_usuarios/', views.listarUsuario, name='lista-usuario'),

    path('delete_usuarios/<int:id>/', views.deleteUsuario, name='delete-usuario'),

    path('alterar_usuarios/<int:id>/', views.alteraUsuario, name='update-usuario'),

    path('usuariosempreendimento/multiplos/', views.criarUsuariosEmpreendimento, name='criar-usuarios-empreendimento'),

    path('delete_usuarios_empreendimento/<int:id>/', views.deleteUsuarioEmpreendimento, name='delete-usuario-empreendimento'),
]

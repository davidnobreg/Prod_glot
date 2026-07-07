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

    path('delete_usuarios_empreendimento/<uuid:usuario_empreendimento_uuid>/', views.deleteUsuarioEmpreendimento, name='delete-usuario-empreendimento'),

    # Grupos de acesso (Fase 2)
    path('grupos/', views.lista_grupos, name='lista_grupos'),
    path('grupos/novo/', views.criar_grupo, name='criar_grupo'),
    path('grupos/<int:pk>/editar/', views.editar_grupo, name='editar_grupo'),
    path('grupos/<int:pk>/excluir/', views.excluir_grupo, name='excluir_grupo'),

    # Associar usuario a grupos (Fase 2 complemento)
    path('usuario/<int:pk>/grupos/', views.associar_grupos, name='associar_grupos'),

    # Impersonate (Fase 3)
    path('usuario/impersonate/stop/', views.impersonate_stop, name='impersonate_stop'),
    path('usuario/<int:pk>/impersonate/', views.impersonate_start, name='impersonate_start'),
]

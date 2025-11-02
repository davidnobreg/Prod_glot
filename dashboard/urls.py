from django.urls import path  # adicionar include
from . import views

urlpatterns = [
    # Cadastro de cliente
    path('', views.listDashboard, name='list-dashboard'),

]

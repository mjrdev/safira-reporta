from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("registrar/", views.registrar, name="registrar"),
    path("protocolo/<str:protocolo>/confirmacao/", views.confirmacao, name="confirmacao"),
    path("protocolo/<str:protocolo>/apoiar/", views.apoiar, name="apoiar"),
    path("consultar/", views.consultar, name="consultar"),
    path("protocolo/<str:protocolo>/", views.consulta_protocolo, name="consulta_protocolo"),
    path("resolvidos/", views.resolvidos, name="resolvidos"),
    path("painel/", views.painel, name="painel"),
    path("painel/relatorio/", views.relatorio, name="relatorio"),
    path("painel/demanda/<str:protocolo>/", views.detalhe, name="detalhe"),
    path("painel/demanda/<str:protocolo>/status/", views.avancar_status, name="avancar_status"),
    path("entrar/", views.LoginView.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
]

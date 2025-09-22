from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('salvar/<int:noticia_id>/', views.botao_salvar_noticia, name='toggle_salvar'),
    path('salvos/', views.noticias_salvas, name='noticias_salvas'),
    path('<int:pk>/', views.noticia_detalhe, name='noticia_detalhe'),
]

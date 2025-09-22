from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('salvar/<int:noticia_id>/', views.toggle_salvar_noticia, name='toggle_salvar'),
    path('salvos/', views.noticias_salvas, name='noticias_salvas'),
]

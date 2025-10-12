# noticias/urls.py
from django.urls import path
from . import views

app_name = "noticias"

urlpatterns = [
    path("", views.index, name="index"),
    path("noticia/<int:pk>/", views.noticia_detalhe, name="noticia_detalhe"),
    path("noticia/<int:pk>/votar/", views.votar, name="votar"),
    path("noticia/<int:pk>/toggle-salvo/", views.toggle_salvo, name="toggle_salvo"),
    path("minhas-salvas/", views.minhas_salvas, name="minhas_salvas"),
    path("signup/", views.signup, name="signup"),
    path("noticia/<int:pk>/resumir/", views.resumir_noticia, name="resumir_noticia"),
]

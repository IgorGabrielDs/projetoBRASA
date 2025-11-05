from django.urls import path
from . import views
from django.conf import settings

app_name = 'noticias'

urlpatterns = [
    path('', views.index, name='index'),
    path('noticia/<int:pk>/', views.noticia_detalhe, name='noticia_detalhe'),
    path('noticia/<int:pk>/votar/', views.votar, name='votar'),
    path('accounts/signup/', views.signup, name='signup'),
    path("salvos/", views.minhas_salvas, name="salvos"),
    path("noticia/<int:pk>/salvar/", views.toggle_salvo, name="toggle_salvo"),
    path('noticia/<int:pk>/resumir/', views.resumir_noticia, name='resumir_noticia'),
]

# 🔐 Somente em ambiente de desenvolvimento/teste (DEBUG=True)
if getattr(settings, "DEBUG", False):
    urlpatterns += [
        path('e2e/login-as/<str:username>/', views.e2e_login_as, name='e2e_login_as'),
    ]

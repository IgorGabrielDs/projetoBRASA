from . import views

app_name = 'noticias'

urlpatterns = [
    path('', views.index, name='index'),
    path('noticia/<int:pk>/', views.noticia_detalhe, name='noticia_detalhe'),
    path('noticia/<int:pk>/votar/', views.votar, name='votar'),
    path('accounts/signup/', views.signup, name='signup'),  
    path("salvos/", views.minhas_salvas, name="salvos"),
    path("noticia/<int:pk>/salvar/", views.toggle_salvo, name="toggle_salvo"),
]

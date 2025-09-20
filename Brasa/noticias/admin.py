from django.contrib import admin
from .models import Noticia, Voto

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'autor', 'categoria', 'data_publicacao', 'destaque')
    list_filter   = ('categoria', 'destaque', 'data_publicacao')
    search_fields = ('titulo', 'conteudo', 'autor')

@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display  = ('noticia', 'usuario', 'valor', 'atualizado_em')
    list_filter   = ('valor', 'atualizado_em')
    search_fields = ('noticia__titulo', 'usuario__username')

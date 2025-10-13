from django.contrib import admin
from .models import Noticia, Voto

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("id","titulo","criado_em")
    search_fields = ("titulo","conteudo")
    ordering = ("-criado_em",)
    fields = ("titulo","conteudo","imagem","legenda","criado_em")
    readonly_fields = ("criado_em",)
@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ("id","noticia","usuario","valor")
    list_filter = ("valor",)

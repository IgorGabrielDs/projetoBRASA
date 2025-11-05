from django.contrib import admin
from .models import Assunto, Noticia, Voto, Salvo


@admin.register(Assunto)
class AssuntoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "slug")
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}
    ordering = ("nome",)


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "criado_em")
    search_fields = ("titulo", "conteudo")
    list_filter = ("assuntos", "criado_em")
    ordering = ("-criado_em",)
    fields = ("titulo", "conteudo", "imagem", "legenda", "assuntos", "criado_em")
    readonly_fields = ("criado_em",)
    autocomplete_fields = ("assuntos",)


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ("id", "noticia", "usuario", "valor")
    list_filter = ("valor",)
    search_fields = ("usuario__username", "noticia__titulo")


@admin.register(Salvo)
class SalvoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "noticia", "criado_em")
    list_filter = ("criado_em",)
    search_fields = ("usuario__username", "noticia__titulo")
    ordering = ("-criado_em",)

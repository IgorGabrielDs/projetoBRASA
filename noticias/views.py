from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Noticia

def home(request):
    noticias = Noticia.objects.order_by('-data_publicacao')
    
    noticias_salvas_ids = []
    if request.user.is_authenticated:
        noticias_salvas_ids = request.user.noticias_salvas.values_list('id', flat=True)

    contexto = {
        'noticias': noticias,   
        'noticias_salvas_ids': noticias_salvas_ids,
    }
    return render(request, 'home.html', contexto)

@login_required
def noticias_salvas(request):
    noticias = request.user.noticias_salvas.order_by('-data_publicacao')
    contexto = {
        'noticias': noticias,
    }
    return render(request, 'noticias_salvas.html', contexto)

@login_required
def botao_salvar_noticia(request, noticia_id):
    noticia = get_object_or_404(Noticia, id=noticia_id)
    
    if noticia in request.user.noticias_salvas.all():
        request.user.noticias_salvas.remove(noticia)
        salvo = False
    else:
        request.user.noticias_salvas.add(noticia)
        salvo = True
        
    
    return JsonResponse({'salvo': salvo})

def noticia_detalhe(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)
    contexto = {
        'noticia': noticia,
    }
    return render(request, 'noticia_detalhe.html', contexto)

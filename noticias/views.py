from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Noticia, Voto

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
    voto_usuario = None
    if request.user.is_authenticated:
        voto_usuario = Voto.objects.filter(noticia=noticia, usuario=request.user).first()
    ctx = {
        'noticia': noticia,
        'score': noticia.score(),
        'up': noticia.upvotes(),
        'down': noticia.downvotes(),
        'voto_usuario': voto_usuario.valor if voto_usuario else 0,
    }
    return render(request, 'noticias/detalhe.html', ctx)

@login_required
def votar(request, pk):
    # aceita POST com 'valor' = "1" ou "-1"
    noticia = get_object_or_404(Noticia, pk=pk)
    if request.method != 'POST':
        return redirect('noticia_detalhe', pk=pk)

    try:
        valor = int(request.POST.get('valor'))
        assert valor in (1, -1)
    except Exception:
        messages.error(request, 'Voto inválido.')
        return redirect('noticia_detalhe', pk=pk)

    voto, created = Voto.objects.get_or_create(noticia=noticia, usuario=request.user, defaults={'valor': valor})

    # clique repetido no mesmo botão desfaz (remove) o voto
    if not created and voto.valor == valor:
        voto.delete()
        status = 'removido'
    else:
        voto.valor = valor
        voto.save(update_fields=['valor', 'atualizado_em'])
        status = 'atualizado'

    # resposta AJAX opcional
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': status,
            'score': noticia.score(),
            'up': noticia.upvotes(),
            'down': noticia.downvotes(),
            'voto_usuario': 0 if status == 'removido' else valor
        })


    return redirect('noticia_detalhe', pk=pk)



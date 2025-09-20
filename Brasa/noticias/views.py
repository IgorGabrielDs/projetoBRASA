from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Noticia, Voto

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
            'meu_voto': 0 if status == 'removido' else valor
        })

    return redirect('noticia_detalhe', pk=pk)
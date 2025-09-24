from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db.models import (Sum, Case, When, IntegerField, Exists, OuterRef, Value, BooleanField)
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Noticia, Voto, Assunto, Salvo
    

def index(request):
    noticias = Noticia.objects.all()
    assuntos = Assunto.objects.all()

    selecionados = request.GET.getlist("assunto")
    periodo = request.GET.get("periodo")
    sort = request.GET.get("sort", "recentes")

    if selecionados:
        noticias = noticias.filter(assuntos__slug__in=selecionados).distinct()

    if periodo in {"24h", "7d", "30d"}:
        dias = {"24h": 1, "7d": 7, "30d": 30}[periodo]
        since = timezone.now() - timedelta(days=dias)
        noticias = noticias.filter(criado_em__gte=since)

    if sort == "populares":
        noticias = noticias.annotate(score=Sum("votos__valor")).order_by("-score", "-criado_em")
    else:
        noticias = noticias.order_by("-criado_em")

    if request.user.is_authenticated:
        noticias = noticias.annotate(
            is_saved=Exists(
                Salvo.objects.filter(usuario=request.user, noticia=OuterRef("pk"))
            )
        )
    else:
        noticias = noticias.annotate(is_saved=Value(False, output_field=BooleanField()))

    top3 = cache.get("top3_semana")
    if top3 is None:
        semana = timezone.now() - timedelta(days=7)
        top3_qs = (
            Noticia.objects.filter(votos__criado_em__gte=semana)
            .annotate(
                score_semanal=Sum("votos__valor"),
                ups_semana=Sum(Case(When(votos__valor=1, then=1), default=0, output_field=IntegerField())),
                downs_semana=Sum(Case(When(votos__valor=-1, then=1), default=0, output_field=IntegerField())),
            )
            .order_by("-score_semanal", "-ups_semana", "-criado_em")[:3]
        )
        top3 = list(top3_qs)
        cache.set("top3_semana", top3, 300)

    ctx = {
        "noticias": noticias,
        "assuntos": assuntos,
        "selecionados": selecionados,
        "periodo": periodo or "",
        "sort": sort,
        "top3": top3,
    }
    return render(request, "noticias/index.html", ctx)

def noticia_detalhe(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)
    voto_usuario = None
    if request.user.is_authenticated:
        voto_usuario = Voto.objects.filter(noticia=noticia, usuario=request.user).first()
        is_saved = noticia.salvos.filter(pk=request.user.pk).exists()
    else:
        is_saved = False

    ctx = {
        'noticia': noticia,
        'score': noticia.score(),
        'up': noticia.upvotes(),
        'down': noticia.downvotes(),
        'voto_usuario': voto_usuario.valor if voto_usuario else 0,
        'is_saved': is_saved,
    }
    return render(request, 'noticias/detalhe.html', ctx)

@login_required
def votar(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)

    if request.method != 'POST':
        return redirect('noticias:noticia_detalhe', pk=pk)

    try:
        valor = int(request.POST.get('valor', 0))
        assert valor in (1, -1)
    except Exception:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Voto inválido.'}, status=400)
        messages.error(request, 'Voto inválido.')
        return redirect('noticias:noticia_detalhe', pk=pk)

    voto, created = Voto.objects.get_or_create(
        noticia=noticia,
        usuario=request.user,
        defaults={'valor': valor}
    )

    if created:
        current = valor
    else:
        if voto.valor == valor:
            voto.delete()
            current = 0
        else:
            voto.valor = valor
            voto.save()
            current = valor

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'up': noticia.upvotes(),
            'down': noticia.downvotes(),
            'score': noticia.score(),
            'voto_usuario': current,
        })

    return redirect('noticias:noticia_detalhe', pk=pk)

def signup(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    if not next_url or next_url == "None":
        next_url = None
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            if user:
                auth_login(request, user)
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a).")
            if next_url:
                return redirect(next_url)
            return redirect("noticias:index")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form, "next": next_url})

@login_required
def minhas_salvas(request):
    noticias = Noticia.objects.filter(salvos=request.user).order_by('-salvo__criado_em')
    for n in noticias:
        n.is_saved = True
    return render(request, "noticias/noticias_salvas.html", {"noticias": noticias})

@login_required
def toggle_salvo(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Método não permitido.")

    noticia = get_object_or_404(Noticia, pk=pk)
    qs = Salvo.objects.filter(usuario=request.user, noticia=noticia)

    if qs.exists():
        qs.delete()
        saved = False
        label = "Ver mais tarde"
        msg = "Removido dos salvos."
    else:
        Salvo.objects.get_or_create(usuario=request.user, noticia=noticia)
        saved = True
        label = "Retirar de Ver mais tarde"
        msg = "Salvo para ler mais tarde."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": saved, "label": label})

    messages.success(request, msg)
    return redirect("noticias:detalhe", pk=pk)

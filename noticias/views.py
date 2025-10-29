from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db.models import (
    Sum, Case, When, IntegerField, Exists, OuterRef, Value, BooleanField
)
from django.db.models import Sum, Case, When, IntegerField, Exists, OuterRef, Value, BooleanField, Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Noticia, Voto, Assunto, Salvo
import google.generativeai as genai


# ==============================================
# RECOMENDAÇÃO — helper simples por afinidade
# ==============================================
def _recomendadas_para_usuario(user, limite=10):
    """
    Retorna um QuerySet de notícias recomendadas por afinidade de assuntos
    com base no histórico do usuário (votos +1 e salvos).
    Critérios de ordenação: match de assuntos, score (up - down) e recência.
    """
    if not user.is_authenticated:
        return Noticia.objects.none()

    # Assuntos de notícias que o usuário votou positivamente
    assuntos_like = Voto.objects.filter(
        usuario=user,
        valor=1
    ).values_list("noticia__assuntos", flat=True)

    # Assuntos de notícias que o usuário salvou
    assuntos_salvos = Salvo.objects.filter(
        usuario=user
    ).values_list("noticia__assuntos", flat=True)

    assuntos_ids = list(assuntos_like) + list(assuntos_salvos)
    assuntos_ids = [a for a in assuntos_ids if a]

    if not assuntos_ids:
        return Noticia.objects.none()

    # Evitar recomendar itens já vistos (votados ou salvos)
    vistos_ids = Noticia.objects.filter(
        Q(votos__usuario=user) | Q(salvo__usuario=user)
    ).values_list("id", flat=True).distinct()

    qs = (
        Noticia.objects.exclude(id__in=vistos_ids)
        .filter(assuntos__in=assuntos_ids)
        .annotate(
            match_count=Count(
                "assuntos",
                filter=Q(assuntos__in=assuntos_ids),
                distinct=True
            )
        )
        .annotate(score=Sum("votos__valor"))
        .order_by("-match_count", "-score", "-criado_em")
        .distinct()[:limite]
    )

    # Anotar se já está salvo, para manter consistência visual
    qs = qs.annotate(
        is_saved=Exists(
            Salvo.objects.filter(usuario=user, noticia=OuterRef("pk"))
        )
    )
    return qs


# ==============================================
# PÁGINA INICIAL / FEED
# ==============================================
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

    # ===== NOVO: bloco de recomendadas por afinidade
    recomendadas = _recomendadas_para_usuario(request.user, limite=8)

    ctx = {
        "noticias": noticias,
        "assuntos": assuntos,
        "selecionados": selecionados,
        "periodo": periodo or "",
        "sort": sort,
        "top3": top3,
        "recomendadas": recomendadas,  # <= NOVO
    }
    return render(request, "noticias/index.html", ctx)


# ==============================================
# DETALHE DE NOTÍCIA
# ==============================================
def noticia_detalhe(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)
    voto_usuario = None
    if request.user.is_authenticated:
        voto_usuario = Voto.objects.filter(noticia=noticia, usuario=request.user).first()
        is_saved = noticia.salvos.filter(pk=request.user.pk).exists()
    else:
        is_saved = False

    ctx = {
        "noticia": noticia,
        "score": noticia.score(),
        "up": noticia.upvotes(),
        "down": noticia.downvotes(),
        "voto_usuario": voto_usuario.valor if voto_usuario else 0,
        "is_saved": is_saved,
    }
    return render(request, "noticias/detalhe.html", ctx)


# ==============================================
# VOTOS / INTERAÇÃO
# ==============================================
@login_required
def votar(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)

    if request.method != "POST":
        return redirect("noticias:noticia_detalhe", pk=pk)

    try:
        valor = int(request.POST.get("valor", 0))
        assert valor in (1, -1)
    except Exception:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Voto inválido."}, status=400)
        messages.error(request, "Voto inválido.")
        return redirect("noticias:noticia_detalhe", pk=pk)

    voto, created = Voto.objects.get_or_create(
        noticia=noticia,
        usuario=request.user,
        defaults={"valor": valor},
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

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "up": noticia.upvotes(),
            "down": noticia.downvotes(),
            "score": noticia.score(),
            "voto_usuario": current,
        })

    return redirect("noticias:noticia_detalhe", pk=pk)


# ==============================================
# CADASTRO / LOGIN
# ==============================================
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


# ==============================================
# SALVOS
# ==============================================
@login_required
def minhas_salvas(request):
    noticias = (
        Noticia.objects.filter(salvo__usuario=request.user)
        .order_by("-salvo__criado_em")
        .distinct()
    )
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


# ==============================================
# RESUMIR NOTÍCIA — versão híbrida (Gemini + fallback)
# ==============================================
@csrf_exempt
def resumir_noticia(request, pk):
    """
    Gera ou atualiza o resumo da notícia e garante persistência no banco.
    Usa Gemini se disponível; se falhar ou não houver chave, usa um fallback local.
    Retorna JSON com {"status":"ok","resumo":"..."}.
    """
    noticia = get_object_or_404(Noticia, pk=pk)
    api_key = getattr(settings, "GEMINI_API_KEY", None)

    fallback_resumo = (
        "Resumo gerado automaticamente para testes E2E BRASA. "
        "Este texto é usado apenas para validação de interface e integração."
    )

    resumo_final = None

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-flash-latest")

            prompt = f"""
            Você é um assistente de jornalismo. Resuma a notícia abaixo de forma clara, objetiva e em português:
            <noticia>
            Título: {noticia.titulo}
            Conteúdo: {noticia.conteudo}
            </noticia>
            """

            response = model.generate_content(prompt)
            resumo = (getattr(response, "text", "") or "").strip()
            if resumo and len(resumo) > 30:
                resumo_final = resumo
        except Exception as e:
            print(f"[AVISO] Falha no Gemini ({e}); usando fallback")

    if not resumo_final:
        resumo_final = fallback_resumo

    noticia.resumo = resumo_final
    noticia.save(update_fields=["resumo"])
    noticia.refresh_from_db(fields=["resumo"])

    return JsonResponse({"status": "ok", "resumo": noticia.resumo})

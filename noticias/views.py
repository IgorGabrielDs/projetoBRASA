from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db.models import (
    Sum, Exists, OuterRef, Value, BooleanField, F, Q
)
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Noticia, Voto, Assunto, Salvo
from django.conf import settings
import openai


# =======================
# FUNÇÃO AUXILIAR
# =======================
def _annotate_is_saved(qs, user):
    """Anota se o usuário salvou a notícia."""
    if user.is_authenticated:
        return qs.annotate(
            is_saved=Exists(
                Salvo.objects.filter(usuario=user, noticia=OuterRef("pk"))
            )
        )
    return qs.annotate(is_saved=Value(False, output_field=BooleanField()))


# =======================
# VIEW PRINCIPAL (HOME)
# =======================
def index(request):
    noticias = Noticia.objects.all()
    assuntos = Assunto.objects.all()

    selecionados = request.GET.getlist("assunto")
    periodo = request.GET.get("periodo")
    sort = request.GET.get("sort", "recentes")

    # -------------------------------
    # Filtros e ordenação da lista principal
    # -------------------------------
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

    noticias = _annotate_is_saved(noticias, request.user)

    # -------------------------------
    # Seções da home (INDEPENDENTES dos filtros da lista)
    # -------------------------------
    all_qs = Noticia.objects.all().select_related().prefetch_related("assuntos")

    # 1) Destaques (com imagem) + score por votos/visualizações
    destaques_qs = all_qs.filter(imagem__isnull=False) \
        .annotate(score_calculado=Sum("votos__valor", default=0) + (F("visualizacoes") * 0.01)) \
        .order_by("-score_calculado", "-criado_em")
    destaques = _annotate_is_saved(destaques_qs, request.user)[:3]
    destaques_ids = list(destaques.values_list("id", flat=True))

    # 2) Para você (personalização simples + fallback)
    if request.user.is_authenticated:
        assuntos_interesse = Assunto.objects.filter(
            noticias__votos__usuario=request.user
        ).values_list("pk", flat=True).distinct()
        assuntos_salvos = Assunto.objects.filter(
            noticias__salvo__usuario=request.user
        ).values_list("pk", flat=True).distinct()
        assuntos_ids = set(list(assuntos_interesse) + list(assuntos_salvos))
        if assuntos_ids:
            pv_qs = all_qs.filter(assuntos__in=assuntos_ids).exclude(id__in=destaques_ids).distinct()
        else:
            pv_qs = all_qs.exclude(id__in=destaques_ids)
    else:
        pv_qs = all_qs.exclude(id__in=destaques_ids)

    para_voce = _annotate_is_saved(pv_qs.order_by("-criado_em"), request.user)[:6]
    if not para_voce.exists():
        # fallback: pega recentes mesmo se não houver interesses/dados suficientes
        para_voce = _annotate_is_saved(all_qs.order_by("-criado_em"), request.user)[:6]

    # 3) Mais lidas (últimos 7 dias)
    since_7 = timezone.now() - timedelta(days=7)
    ml_qs = all_qs.filter(criado_em__gte=since_7).order_by("-visualizacoes", "-criado_em")
    mais_lidas = _annotate_is_saved(ml_qs, request.user)[:2]
    if not mais_lidas.exists():
        mais_lidas = _annotate_is_saved(all_qs.order_by("-criado_em"), request.user)[:2]

    # 4) JC360 (slug OU nome) + fallbacks em 3 etapas
    try:
        jc360_assunto = Assunto.objects.get(slug="jc360")
        jc360_qs = all_qs.filter(assuntos=jc360_assunto)
    except Assunto.DoesNotExist:
        jc360_qs = all_qs.filter(assuntos__nome__iexact="jc360")

    jc360 = _annotate_is_saved(jc360_qs.order_by("-criado_em"), request.user)[:4]

    # Fallback 1: recentes fora dos destaques
    if not jc360.exists():
        jc360 = _annotate_is_saved(
            all_qs.exclude(id__in=destaques_ids).order_by("-criado_em"),
            request.user
        )[:4]

    # Fallback 2: recentes gerais (sem excluir nada)
    if not jc360.exists():
        jc360 = _annotate_is_saved(
            all_qs.order_by("-criado_em"),
            request.user
        )[:4]


    # 5) Vídeos (slug OU nome) + fallback se vazio
    try:
        videos_assunto = Assunto.objects.get(slug="videos")
        videos_qs = all_qs.filter(assuntos=videos_assunto)
    except Assunto.DoesNotExist:
        videos_qs = all_qs.filter(assuntos__nome__iexact="videos")

    videos = _annotate_is_saved(videos_qs.order_by("-criado_em"), request.user)[:2]
    if not videos.exists():
        videos = _annotate_is_saved(all_qs.order_by("-criado_em"), request.user)[:2]

    # 6) Pernambuco (slug OU nome) — 1 destaque
    try:
        pe_assunto = Assunto.objects.get(slug="pernambuco")
        pernambuco = all_qs.filter(assuntos=pe_assunto).order_by("-criado_em").first()
    except Assunto.DoesNotExist:
        pernambuco = all_qs.filter(assuntos__nome__iexact="pernambuco").order_by("-criado_em").first()
    if not pernambuco:
        pernambuco = all_qs.order_by("-criado_em").first()

    # 7) Top 3 da semana (cacheado)
    top3 = cache.get("top3_semana_final")
    if top3 is None:
        hoje = timezone.now().date()
        inicio = hoje - timedelta(days=6)
        top3_qs = (
            Noticia.objects.filter(criado_em__date__gte=inicio)
            .annotate(
                score_calculado=Sum("votos__valor", default=0) + (F("visualizacoes") * 0.01)
            )
            .order_by("-score_calculado", "-criado_em")[:3]
        )
        top3 = list(top3_qs)
        cache.set("top3_semana_final", top3, 300)

    ctx = {
        "noticias": noticias,
        "assuntos": assuntos,
        "selecionados": selecionados,
        "periodo": periodo or "",
        "sort": sort,

        # Seções da home
        "destaques": destaques,
        "para_voce": para_voce,
        "mais_lidas": mais_lidas,
        "jc360": jc360,
        "videos": videos,
        "pernambuco": pernambuco,
        "top3": top3,
    }

    return render(request, "noticias/index.html", ctx)


# =======================
# DETALHE DA NOTÍCIA
# =======================
def noticia_detalhe(request, pk):
    noticia = get_object_or_404(Noticia, pk=pk)
    noticia.visualizacoes = (noticia.visualizacoes or 0) + 1
    noticia.save(update_fields=["visualizacoes"])

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


# =======================
# VOTAR (AJAX)
# =======================
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
        noticia=noticia, usuario=request.user, defaults={"valor": valor}
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


# =======================
# SIGNUP
# =======================
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


# =======================
# SALVOS
# =======================
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
    return redirect("noticias:noticia_detalhe", pk=pk)


# =======================
# RESUMO (IA)
# =======================
def resumir_noticia(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido."}, status=405)

    noticia = get_object_or_404(Noticia, pk=pk)

    if noticia.resumo:
        return JsonResponse({"resumo": noticia.resumo})

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente de jornalismo que cria resumos concisos e informativos.",
                },
                {
                    "role": "user",
                    "content": f"Resuma a seguinte notícia em um único parágrafo em português: {noticia.conteudo}",
                },
            ],
            temperature=0.7,
            max_tokens=150,
        )

        resumo_gerado = response.choices[0].message.content.strip()
        noticia.resumo = resumo_gerado
        noticia.save(update_fields=["resumo"])
        return JsonResponse({"resumo": resumo_gerado})

    except Exception as e:
        return JsonResponse(
            {"error": f"Erro ao conectar/gerar com a OpenAI: {e}"}, status=502
        )

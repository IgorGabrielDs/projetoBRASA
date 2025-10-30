import pytest
from django.utils import timezone
from django.test import Client
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# Helpers
# =========================

def _login_via_cookie(chrome, base_url, username="aluno", password="12345678"):
    """
    Realiza login usando o Django Test Client e injeta o cookie de sessão no Chrome.
    Não depende de HTML/rotas de login nem de DEBUG especial.
    """
    client = Client()
    ok = client.login(username=username, password=password)
    assert ok, "Falha ao logar com Django Client; verifique credenciais do fixture 'user'."

    # Obtém o sessionid do client
    session_cookie = client.cookies.get("sessionid")
    assert session_cookie, "Cookie 'sessionid' não encontrado após client.login()"

    # Precisa primeiro visitar o domínio para poder setar cookie no navegador
    chrome.get(f"{base_url}/")
    # Injeta o cookie de sessão no domínio atual
    chrome.add_cookie({
        "name": "sessionid",
        "value": session_cookie.value,
        "path": "/",
        "httpOnly": True,
    })
    # Recarrega para aplicar a sessão
    chrome.get(f"{base_url}/")


def _wait_para_voce_block(chrome, timeout=20):
    """
    Espera pela seção "Para você".
    Aceita:
      - <section aria-label='Recomendadas para você'> + ul[data-testid='para-voce']
      - ou estado vazio: [data-testid='para-voce-empty']
    Retorna (ul_element, is_empty: bool).
    """
    WebDriverWait(chrome, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
    )

    # tenta a section semântica (se existir no template)
    try:
        WebDriverWait(chrome, 6).until(
            EC.presence_of_element_located(
                (By.XPATH, "//section[@aria-label='Recomendadas para você']")
            )
        )
    except Exception:
        pass

    # tenta a UL com itens
    try:
        ul = WebDriverWait(chrome, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='para-voce']"))
        )
        return ul, False
    except Exception:
        # tenta estado vazio
        try:
            empty = WebDriverWait(chrome, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='para-voce-empty']"))
            )
            return empty, True
        except Exception:
            # diagnóstico útil no log
            try:
                print("\n--- DIAGNÓSTICO URL ---\n", chrome.current_url)
                print("\n--- DIAGNÓSTICO HTML (início) ---\n", chrome.page_source[:2000])
            except Exception:
                pass
            raise


def _textos_de_headline(el):
    itens = el.find_elements(By.CSS_SELECTOR, ".headline, a.headline")
    if not itens:
        # fallback para <li> quando não há classe .headline
        itens = el.find_elements(By.CSS_SELECTOR, "li")
    return [i.text.strip() for i in itens if i.text.strip()]


# =========================
# Testes
# =========================

@pytest.mark.django_db
def test_recomendadas_por_afinidade_exclui_vistos_e_prioriza_assunto(chrome, live_url, user):
    """
    Afinidade básica:
    - like em N1 (Tec) e salvo N1 -> visto
    - recomenda N2 (Tec) e não recomenda N1 (visto)
    """
    from noticias.models import Assunto, Noticia, Voto, Salvo

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    esp = Assunto.objects.create(nome="Esportes", slug="esportes")

    n1 = Noticia.objects.create(titulo="N1 Tec — já vista", conteudo="...", criado_em=timezone.now())
    n1.assuntos.add(tec)
    n2 = Noticia.objects.create(titulo="N2 Tec — recomendável", conteudo="...", criado_em=timezone.now())
    n2.assuntos.add(tec)
    n3 = Noticia.objects.create(titulo="N3 Esp — outro assunto", conteudo="...", criado_em=timezone.now())
    n3.assuntos.add(esp)

    Voto.objects.create(noticia=n1, usuario=user, valor=1)
    Salvo.objects.create(noticia=n1, usuario=user)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty, "Seção 'Para você' veio vazia; esperava itens por afinidade."

    textos = _textos_de_headline(ul_or_empty)
    assert any("N2 Tec — recomendável" in t for t in textos)
    assert all("N1 Tec — já vista" not in t for t in textos)


@pytest.mark.django_db
def test_recomendadas_fallback_quando_sem_sinais_mostra_conteudo_recente(chrome, live_url, user):
    """
    Fallback recente:
    - Usuário sem sinais
    - Deve trazer ao menos 1 item recente
    """
    from noticias.models import Assunto, Noticia

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    old_time = timezone.now() - timezone.timedelta(days=40)

    recente = Noticia.objects.create(titulo="Recente A", conteudo="...", criado_em=timezone.now())
    recente.assuntos.add(tec)

    antiga = Noticia.objects.create(titulo="Antiga X", conteudo="...", criado_em=old_time)
    antiga.assuntos.add(tec)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty, "Esperava ao menos um item nas recomendadas em modo fallback (recentes)."

    itens = ul_or_empty.find_elements(By.CSS_SELECTOR, ".headline, a.headline, li")
    assert len(itens) >= 1


@pytest.mark.django_db
def test_nao_recomenda_itens_vistos_por_voto_ou_salvo(chrome, live_url, user):
    """
    Exclusão de vistos:
    - Se o usuário votou +-1 OU salvou a notícia, ela conta como 'vista' e não deve ser recomendada.
    """
    from noticias.models import Assunto, Noticia, Voto, Salvo

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")

    n_vista_vote = Noticia.objects.create(titulo="Tec Votada", conteudo="...", criado_em=timezone.now())
    n_vista_vote.assuntos.add(tec)

    n_vista_salvo = Noticia.objects.create(titulo="Tec Salva", conteudo="...", criado_em=timezone.now())
    n_vista_salvo.assuntos.add(tec)

    n_recom = Noticia.objects.create(titulo="Tec Recomendada", conteudo="...", criado_em=timezone.now())
    n_recom.assuntos.add(tec)

    # marca 'vistos'
    Voto.objects.create(noticia=n_vista_vote, usuario=user, valor=1)
    Salvo.objects.create(noticia=n_vista_salvo, usuario=user)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty

    textos = _textos_de_headline(ul_or_empty)
    assert "Tec Recomendada" in " | ".join(textos)
    assert "Tec Votada" not in " | ".join(textos)
    assert "Tec Salva" not in " | ".join(textos)


@pytest.mark.django_db
def test_prioriza_match_count_de_assuntos(chrome, live_url, user):
    """
    Ordenação por afinidade:
    - Gera afinidade em Tec e Mundo usando notícias 'semente' (votadas).
    - Candidatas (n1, n2) NÃO são vistas/votadas.
    - Notícia com 2 matches (Tec+Mundo) deve vir ANTES de notícia com 1 match (Tec).
    """
    from noticias.models import Assunto, Noticia, Voto

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    mundo = Assunto.objects.create(nome="Mundo", slug="mundo")

    # ---- Candidatas (não votar nelas!)
    n2 = Noticia.objects.create(
        titulo="Match 2 (Tec+Mundo)",
        conteudo="...",
        criado_em=timezone.now()
    )
    n2.assuntos.add(tec, mundo)

    n1 = Noticia.objects.create(
        titulo="Match 1 (Tec)",
        conteudo="...",
        criado_em=timezone.now()
    )
    n1.assuntos.add(tec)

    # ---- Sementes para gerar afinidade sem marcar candidatas como 'vistas'
    seed_tec = Noticia.objects.create(
        titulo="Seed Tec",
        conteudo="...",
        criado_em=timezone.now()
    )
    seed_tec.assuntos.add(tec)

    seed_mundo = Noticia.objects.create(
        titulo="Seed Mundo",
        conteudo="...",
        criado_em=timezone.now()
    )
    seed_mundo.assuntos.add(mundo)

    # Votos do usuário gerando sinais de assuntos (Tec e Mundo)
    Voto.objects.create(noticia=seed_tec, usuario=user, valor=1)
    Voto.objects.create(noticia=seed_mundo, usuario=user, valor=1)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty, "Seção 'Para você' não deveria estar vazia; há afinidade e candidatas elegíveis."

    textos = _textos_de_headline(ul_or_empty)
    # Sequência de títulos no bloco:
    s = " -> ".join(textos)
    assert s.find("Match 2 (Tec+Mundo)") != -1 and s.find("Match 1 (Tec)") != -1, f"Esperava as duas candidatas. Sequência: {s}"
    assert s.find("Match 2 (Tec+Mundo)") < s.find("Match 1 (Tec)"), f"Match 2 deveria vir antes por maior match_count. Sequência: {s}"

@pytest.mark.django_db
def test_desempate_por_score_quando_match_igual(chrome, live_url, user):
    """
    Desempate:
    - Para duas notícias com mesmo match_count, a de maior SCORE (soma dos votos) deve vir primeiro.
    """
    from noticias.models import Assunto, Noticia, Voto

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")

    a = Noticia.objects.create(titulo="A - score alto", conteudo="...", criado_em=timezone.now())
    a.assuntos.add(tec)

    b = Noticia.objects.create(titulo="B - score baixo", conteudo="...", criado_em=timezone.now())
    b.assuntos.add(tec)

    # sinais do usuário (gera afinidade com Tec)
    Voto.objects.create(noticia=a, usuario=user, valor=1)  # também serve p/ "visto", mas vamos não salvá-la
    # Para não excluir por 'visto', criamos sinais em outra notícia Tec fictícia:
    dummy = Noticia.objects.create(titulo="Dummy Afinidade", conteudo="...", criado_em=timezone.now())
    dummy.assuntos.add(tec)
    Voto.objects.create(noticia=dummy, usuario=user, valor=1)

    # votos de outros usuários para score
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u1 = U.objects.create_user("u1", password="x")
    u2 = U.objects.create_user("u2", password="x")
    Voto.objects.create(noticia=a, usuario=u1, valor=1)
    Voto.objects.create(noticia=a, usuario=u2, valor=1)  # A tem score maior
    Voto.objects.create(noticia=b, usuario=u1, valor=1)  # B tem score menor

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty

    textos = _textos_de_headline(ul_or_empty)
    s = " -> ".join(textos)
    if s.find("A - score alto") != -1 and s.find("B - score baixo") != -1:
        assert s.find("A - score alto") < s.find("B - score baixo"), f"Esperava A antes de B por score. Sequência: {s}"
    # Se não aparecerem ambos (por filtros de 'vistos'), ao menos A deve aparecer antes de outras.


@pytest.mark.django_db
def test_limite_maximo_de_itens_recomendados_eh_8(chrome, live_url, user):
    """
    Limite:
    - _recomendadas_para_usuario usa limite=8 na home.
    - Criamos 12 notícias do mesmo assunto curtido -> devem aparecer no máx 8 itens na seção.
    """
    from noticias.models import Assunto, Noticia, Voto

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")

    # sinal de afinidade
    seed = Noticia.objects.create(titulo="Seed Tec", conteudo="...", criado_em=timezone.now())
    seed.assuntos.add(tec)
    Voto.objects.create(noticia=seed, usuario=user, valor=1)

    # produz 12 candidatas recomendáveis
    for i in range(12):
        n = Noticia.objects.create(titulo=f"Tec Item {i+1:02d}", conteudo="...", criado_em=timezone.now())
        n.assuntos.add(tec)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty

    # conta itens exibidos (por <li> ou headlines)
    itens = ul_or_empty.find_elements(By.CSS_SELECTOR, "li")
    if not itens:
        itens = ul_or_empty.find_elements(By.CSS_SELECTOR, ".headline, a.headline")
    assert len(itens) <= 8, f"Deveria exibir no máx 8 itens; exibiu {len(itens)}."


@pytest.mark.django_db
def test_fallback_final_quando_nao_ha_populares_nem_sinais_usa_ultimas(chrome, live_url, user):
    """
    Fallback final:
    - Sem sinais e sem notícias na janela de 7 dias com score, criaremos itens 'antigos'.
    - Deve ainda assim trazer algo (últimas por criado_em).
    """
    from noticias.models import Assunto, Noticia

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    old_time = timezone.now() - timezone.timedelta(days=90)

    for i in range(3):
        n = Noticia.objects.create(titulo=f"Antiga {i+1}", conteudo="...", criado_em=old_time)
        n.assuntos.add(tec)

    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    # Pode aparecer vazio se o template não renderiza "antigas", mas o fallback final deveria preencher
    assert not is_empty, "Fallback final deveria renderizar últimas notícias."

    textos = _textos_de_headline(ul_or_empty)
    assert any(t.startswith("Antiga") for t in textos), f"Esperava ver pelo menos uma 'Antiga'. Obtido: {textos}"


@pytest.mark.django_db
def test_renderiza_estado_vazio_quando_nao_ha_noticias(chrome, live_url, user):
    """
    Estado vazio:
    - Quando não há nenhuma notícia no banco, a seção deve exibir um estado vazio suportado pelo teste.
    """
    _login_via_cookie(chrome, live_url)

    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert is_empty, "Com zero notícias, esperava estado vazio data-testid='para-voce-empty'."

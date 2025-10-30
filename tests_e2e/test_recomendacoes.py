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
        # sem 'domain' para o Chrome assumir o host atual do live_server
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


# =========================
# Testes
# =========================

@pytest.mark.django_db
def test_recomendadas_por_afinidade_exclui_vistos_e_prioriza_assunto(chrome, live_url, user):
    """
    Cenário:
    - Usuário logado.
    - Curtiu (votou +1) em uma notícia de 'Tecnologia' (N1).
    - Existem outras notícias de 'Tecnologia' (N2) e de 'Esportes' (N3).

    Espera:
    - Seção 'Para você' aparece.
    - Lista inclui N2 (mesmo assunto), não inclui N1 (já vista/salva).
    """
    from noticias.models import Assunto, Noticia, Voto, Salvo

    # ----- Dados base (recentes)
    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    esp = Assunto.objects.create(nome="Esportes", slug="esportes")

    n1 = Noticia.objects.create(
        titulo="N1 Tec — já vista",
        conteudo="...",
        criado_em=timezone.now()
    )
    n1.assuntos.add(tec)

    n2 = Noticia.objects.create(
        titulo="N2 Tec — recomendável",
        conteudo="...",
        criado_em=timezone.now()
    )
    n2.assuntos.add(tec)

    n3 = Noticia.objects.create(
        titulo="N3 Esp — outro assunto",
        conteudo="...",
        criado_em=timezone.now()
    )
    n3.assuntos.add(esp)

    # ----- Interações do usuário (afinidade + visto)
    Voto.objects.create(noticia=n1, usuario=user, valor=1)  # like em N1
    Salvo.objects.create(noticia=n1, usuario=user)          # marca como visto

    # ----- Login via cookie de sessão
    _login_via_cookie(chrome, live_url, username="aluno", password="12345678")

    # ----- Seção "Para você"
    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    assert not is_empty, "Seção 'Para você' veio vazia; esperava itens por afinidade."

    # ----- Coletar títulos dentro da seção
    itens = ul_or_empty.find_elements(By.CSS_SELECTOR, ".headline, a.headline")
    textos = [i.text.strip() for i in itens if i.text.strip()]

    assert any("N2 Tec — recomendável" in t for t in textos), \
        "Esperava recomendar N2 (mesmo assunto curtido)."
    assert all("N1 Tec — já vista" not in t for t in textos), \
        "Não deve recomendar notícia já vista/salva (N1)."


@pytest.mark.django_db
def test_recomendadas_fallback_quando_sem_sinais_mostra_conteudo_recente(chrome, live_url, user):
    """
    Cenário:
    - Usuário logado porém sem votos/salvos.
    - Há notícias recentes e antigas.

    Espera (checagem conservadora):
    - Seção 'Para você' aparece.
    - Pelo menos 1 item recomendado (fallback recentes/populares).
    """
    from noticias.models import Assunto, Noticia

    tec = Assunto.objects.create(nome="Tecnologia", slug="tecnologia")
    old_time = timezone.now() - timezone.timedelta(days=40)

    recente = Noticia.objects.create(
        titulo="Recente A",
        conteudo="...",
        criado_em=timezone.now()
    )
    recente.assuntos.add(tec)

    antiga = Noticia.objects.create(
        titulo="Antiga X",
        conteudo="...",
        criado_em=old_time
    )
    antiga.assuntos.add(tec)

    # ----- Login via cookie de sessão
    _login_via_cookie(chrome, live_url, username="aluno", password="12345678")

    # ----- Seção "Para você"
    ul_or_empty, is_empty = _wait_para_voce_block(chrome)
    if is_empty:
        raise AssertionError("Esperava ao menos um item nas recomendadas em modo fallback.")

    itens = ul_or_empty.find_elements(By.CSS_SELECTOR, ".headline, a.headline, li")
    assert len(itens) >= 1, "Esperava ao menos um item nas recomendadas em modo fallback."

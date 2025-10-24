import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from django.utils.text import slugify
from django.apps import apps
from django.contrib.auth import get_user_model

# ==============================================
# MODELOS E HELPERS
# ==============================================
Noticia = apps.get_model("noticias", "Noticia")

def _pause(sec=1.0):
    time.sleep(sec)

def _wait_for(driver, by, selector, timeout=12):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def _first_article_link(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, "a[data-testid='article-link']")
    except NoSuchElementException:
        return driver.find_element(By.CSS_SELECTOR, "a[href*='/noticia/']")

def _mk_noticia(db):
    model_fields = {f.name for f in Noticia._meta.get_fields() if getattr(f, "concrete", False)}
    m2m_fields = {f.name for f in Noticia._meta.many_to_many}
    data = {}
    if "titulo" in model_fields: data["titulo"] = "[BRASA] Notícia E2E"
    if "conteudo" in model_fields: data["conteudo"] = "Conteúdo completo E2E BRASA."
    if "resumo" in model_fields: data["resumo"] = ""
    if "legenda" in model_fields: data["legenda"] = "Legenda E2E BRASA"
    if "slug" in model_fields: data["slug"] = slugify("[BRASA] Notícia E2E")
    n = Noticia.objects.create(**data)

    if "assuntos" in m2m_fields:
        try:
            Assunto = apps.get_model("noticias", "Assunto")
            a, _ = Assunto.objects.get_or_create(
                nome="Tecnologia",
                defaults={"slug": slugify("Tecnologia")[:80]},
            )
            n.assuntos.add(a)
        except Exception:
            pass
    return n

# ---------------- login BEST-EFFORT (nunca bloqueia) ----------------
def _login_if_available(chrome, live_url, username="e2e_user", password="teste123", db=None):
    """
    Tenta logar se existir formulário de login. Nunca lança exceção nem trava teste.
    """
    try:
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            kwargs = {"username": username}
            if "email" in [f.name for f in User._meta.get_fields()]:
                kwargs.setdefault("email", "e2e@brasa.com")
            User.objects.create_user(**kwargs, password=password)

        login_urls = ["/login/", "/accounts/login/", "/accounts/signin/"]
        for path in login_urls:
            try:
                chrome.get(live_url + path)
                _pause(0.3)

                # procura campos
                inputs = chrome.find_elements(
                    By.CSS_SELECTOR,
                    "input[name='username'], input[name='email'], #id_username, #id_email"
                )
                pwds = chrome.find_elements(
                    By.CSS_SELECTOR,
                    "input[name='password'], #id_password, input[type='password']"
                )
                if not (inputs and pwds):
                    # não é uma tela de login; tenta próxima rota
                    continue

                # preenche
                try:
                    inputs[0].clear(); inputs[0].send_keys(username)
                    pwds[0].clear();   pwds[0].send_keys(password)
                except Exception:
                    pass

                # submete
                submitted = False
                for sel in (
                    "form [type='submit']",
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:not([type])",
                    "[data-testid='btn-login']",
                ):
                    btns = chrome.find_elements(By.CSS_SELECTOR, sel)
                    if btns:
                        try:
                            btns[0].click()
                            submitted = True
                            break
                        except Exception:
                            continue
                if not submitted:
                    try:
                        pwds[0].send_keys("\n")
                    except Exception:
                        pass

                # aguarda pequeno possível redirect, mas não falha se não houver
                try:
                    WebDriverWait(chrome, 4).until(
                        lambda d: (
                            "/login" not in d.current_url
                            and "/accounts/login" not in d.current_url
                            and "/accounts/signin" not in d.current_url
                        ) or d.find_elements(By.CSS_SELECTOR, "[data-testid='btn-logout'], a[href*='logout']")
                    )
                except TimeoutException:
                    pass

                # tentou uma tela de login; encerra helper
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False

# --------------- resumo helpers ---------------
RESUMO_SELECTORS = [
    "[data-testid='resumo-text']",
    "[data-testid='resumo']",
    "#resumo",
    ".resumo",
]
RESUMO_ERROR_SELECTORS = [
    "[data-testid='resumo-error']",
    ".resumo-error",
    "#resumo-error",
]

def _try_find_any(driver, selectors):
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            return els[0]
    return None

def _get_resumo_text_or_empty(driver):
    el = _try_find_any(driver, RESUMO_SELECTORS)
    return el.text.strip() if el else ""

def _wait_resumo_updated_or_error(driver, previous_text, timeout=45):
    def _cond(d):
        err = _try_find_any(d, RESUMO_ERROR_SELECTORS)
        if err and err.text.strip():
            raise AssertionError(f"Erro ao resumir: {err.text.strip()}")

        if "/login" in d.current_url or "/accounts/login" in d.current_url:
            raise AssertionError("Redirecionado para login ao resumir.")

        el = _try_find_any(d, RESUMO_SELECTORS)
        if el:
            txt = el.text.strip()
            if txt and txt != previous_text:
                return True
        return False
    WebDriverWait(driver, timeout).until(_cond)

RESUMIR_BTN_SELECTORS = [
    "[data-testid='btn-resumir']",
    "button#btn-resumir",
    "button[name='resumir']",
    "button[aria-label*='Resumir']",
    "[data-action='resumir']",
    "[data-role='resumir']",
]

def _click_resumir(chrome):
    for sel in RESUMIR_BTN_SELECTORS:
        try:
            btn = WebDriverWait(chrome, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            # tenta click normal; se falhar, usa JS
            try:
                btn.click()
            except Exception:
                chrome.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            continue
    return False

# ==============================================
# TESTES
# ==============================================
def test_home_lista_artigos(chrome, live_url, db):
    _mk_noticia(db)
    chrome.get(live_url + "/")
    _pause()
    assert "BRASA" in chrome.title or "Notícias" in chrome.title
    assert _first_article_link(chrome).is_displayed()

def test_detalhe_exibe_resumo(chrome, live_url, db):
    n = _mk_noticia(db)
    chrome.get(live_url + "/")
    _first_article_link(chrome).click()
    _pause()
    assert "Resumo" in chrome.page_source or n.resumo[:6] in chrome.page_source

def test_resumir_gera_texto(chrome, live_url, db):
    _login_if_available(chrome, live_url, db=db)

    n = _mk_noticia(db)
    chrome.get(live_url + f"/noticia/{n.pk}/")

    # 1️⃣ Verifica botão
    assert _click_resumir(chrome), "Botão 'Resumir' não encontrado ou não clicável"

    before = _get_resumo_text_or_empty(chrome)

    # 2️⃣ Espera o novo resumo aparecer
    try:
        _wait_resumo_updated_or_error(chrome, previous_text=before, timeout=45)
    except TimeoutException:
        assert False, "Tempo limite atingido: o resumo não apareceu nem mudou."

    after = _get_resumo_text_or_empty(chrome)
    assert after and after != before, "Resumo não foi alterado após clicar em 'Resumir'."
    assert 40 <= len(after) <= 1200, f"Tamanho inesperado do resumo: {len(after)}"

    # 3️⃣ Testa persistência real (reload)
    chrome.refresh()
    WebDriverWait(chrome, 10).until(lambda d: _get_resumo_text_or_empty(d) != "")
    persisted = _get_resumo_text_or_empty(chrome)

    assert persisted == after, (
        f"Resumo não persistiu após reload. "
        f"Antes: {after[:60]!r}... | Depois: {persisted[:60]!r}..."
    )

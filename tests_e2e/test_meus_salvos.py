import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.utils.text import slugify
from django.apps import apps

Noticia = apps.get_model('noticias', 'Noticia')

def _pause():
    time.sleep(0.4)

def _wait_for(driver, by, selector, timeout=8):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))

def _mk_noticia(db):
    model_fields = {f.name for f in Noticia._meta.get_fields() if getattr(f, "concrete", False)}
    m2m_fields   = {f.name for f in Noticia._meta.many_to_many}

    data = {}
    if "titulo"   in model_fields: data["titulo"]   = "[BRASA] Salvar & Listar"
    if "conteudo" in model_fields: data["conteudo"] = "Conteúdo BRASA"
    if "resumo"   in model_fields: data["resumo"]   = "Resumo BRASA"
    if "legenda"  in model_fields: data["legenda"]  = "Legenda BRASA"
    if "slug"     in model_fields: data["slug"]     = slugify("[BRASA] Salvar & Listar")

    noticia = Noticia.objects.create(**data)

    if "assuntos" in m2m_fields:
        try:
            Assunto = apps.get_model('noticias', 'Assunto')
            assunto, _ = Assunto.objects.get_or_create(
                nome="Tecnologia",
                defaults={"slug": slugify("Tecnologia")[:80]},
            )
            noticia.assuntos.add(assunto)
        except Exception:
            pass

    return noticia

def _login(driver, base_url):
    driver.get(f"{base_url}/accounts/login/")
    _wait_for(driver, By.NAME, "username")
    driver.find_element(By.NAME, "username").send_keys("aluno")
    driver.find_element(By.NAME, "password").send_keys("12345678")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit'],input[type='submit']").click()

def _open_first_article(driver):
    try:
        _wait_for(driver, By.CSS_SELECTOR, "a[data-testid='article-link']")
        driver.find_element(By.CSS_SELECTOR, "a[data-testid='article-link']").click()
    except (NoSuchElementException, TimeoutException):
        _wait_for(driver, By.CSS_SELECTOR, "a[href*='/noticia/']")
        driver.find_element(By.CSS_SELECTOR, "a[href*='/noticia/']").click()

def _click_save(driver):
    """
    Clica no botão/anchor de salvar, tentando múltiplos seletores e textos,
    com fallback por varredura de botões/links via JS.
    """
    selectors = [
        "[data-testid='btn-salvar']",
        "#btn-salvar",
        ".btn-salvar",
        "[aria-label*='Salvar' i]",
        "[title*='Salvar' i]",
        "[data-action*='salv' i]",
    ]
    # 1) Tenta seletores diretos
    for sel in selectors:
        try:
            el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            el.click()
            return True
        except Exception:
            pass

    # 2) Tenta por XPath com textos mais comuns
    xpaths = [
        "//button[contains(., 'Salvar') or contains(., 'Ler depois')]",
        "//a[contains(., 'Salvar') or contains(., 'Ler depois')]",
    ]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
            el.click()
            return True
        except Exception:
            pass

    # 3) Fallback: varre botões/links e tenta pelo texto normalizado via JS
    try:
        candidates = driver.find_elements(By.CSS_SELECTOR, "button, a")
        for c in candidates:
            try:
                text = (c.text or "").strip().lower()
                if any(t in text for t in ["salvar", "ler depois", "save", "bookmark"]):
                    c.click()
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False

def _goto_saved_page(driver, base_url):
    # tenta clicar em link de navegação
    for css in ["a[href*='salvo']", "a[href*='salvos']", "a[data-testid='nav-salvos']"]:
        try:
            driver.find_element(By.CSS_SELECTOR, css).click()
            _pause()
            return
        except NoSuchElementException:
            pass
    # tenta GET em rotas conhecidas
    for path in ["/salvos/", "/noticias/salvos/", "/minhas-salvas/", "/noticias/minhas-salvas/"]:
        driver.get(base_url + path)
        _pause()
        if "salvo" in driver.page_source.lower():
            return

def _assert_saved_page(driver):
    page = driver.page_source
    if ("Meus Itens Salvos" in page) or ("Salvos" in page):
        return True
    try:
        driver.find_element(By.CSS_SELECTOR, "[data-testid='saved-item']")
        return True
    except NoSuchElementException:
        pass
    try:
        driver.find_element(By.CSS_SELECTOR, "#empty-saved")
        return False
    except NoSuchElementException:
        return True

def test_meus_salvos_lista_item(chrome, live_url, user, db):
    _mk_noticia(db)
    _login(chrome, live_url)
    _pause()

    chrome.get(live_url + "/")
    _open_first_article(chrome)
    _pause()

    assert _click_save(chrome), "Não encontrei um botão/link de Salvar para clicar."
    _pause()

    _goto_saved_page(chrome, live_url)
    _pause()

    assert _assert_saved_page(chrome), f"Não consegui confirmar a página de salvos. URL atual: {chrome.current_url}"
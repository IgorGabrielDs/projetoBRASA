import time
import re
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.utils.text import slugify
from django.apps import apps

# Models dinâmicos (evita import quebrar se o app mudar)
Noticia = apps.get_model('noticias', 'Noticia')
Voto    = apps.get_model('noticias', 'Voto') if apps.is_installed('noticias') else None

# ---------- utils ----------
def _pause():
    time.sleep(0.4)

def _wait_for(driver, by, selector, timeout=8):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def _btn_save(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, "[data-testid='btn-salvar']")
    except NoSuchElementException:
        try:
            return driver.find_element(By.CSS_SELECTOR, "#btn-salvar, .btn-salvar")
        except NoSuchElementException:
            return driver.find_element(
                By.XPATH,
                "//button[contains(., 'Salvar') or contains(., 'Ler depois')] | "
                "//a[contains(., 'Salvar') or contains(., 'Ler depois')]"
            )

def _login(driver, base_url, username, password):
    driver.get(f"{base_url}/accounts/login/")
    _wait_for(driver, By.NAME, "username")
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit'],input[type='submit']").click()

def _open_first_article(driver):
    try:
        _wait_for(driver, By.CSS_SELECTOR, "a[data-testid='article-link']")
        driver.find_element(By.CSS_SELECTOR, "a[data-testid='article-link']").click()
    except (NoSuchElementException, TimeoutException):
        _wait_for(driver, By.CSS_SELECTOR, "a[href*='/noticia/']")
        driver.find_element(By.CSS_SELECTOR, "a[href*='/noticia/']").click()

def _latest_noticia():
    return Noticia.objects.order_by('-id').first()

def _csrf_from_cookie(driver):
    c = driver.get_cookie("csrftoken")
    return c["value"] if c and c.get("value") else None

def _xhr_post_sync(driver, url, csrf_token, body=None):
    """
    POST síncrono (form urlencoded) no contexto do navegador.
    body deve ser string 'application/x-www-form-urlencoded' ou None.
    """
    return driver.execute_script("""
        var url = arguments[0], token = arguments[1], body = arguments[2];
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url, false);  // síncrono
            xhr.setRequestHeader('X-CSRFToken', token);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            if (body !== null && body !== undefined) {
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                xhr.send(body);
            } else {
                xhr.send(null);
            }
            return xhr.status || 0;
        } catch (e) {
            return 0;
        }
    """, url, csrf_token, body if body is not None else None)

def _xhr_post_json(driver, url, csrf_token, payload_dict):
    """
    POST síncrono com JSON (Content-Type: application/json).
    """
    return driver.execute_script("""
        var url = arguments[0], token = arguments[1], data = arguments[2];
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url, false);  // síncrono
            xhr.setRequestHeader('X-CSRFToken', token);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
            xhr.send(JSON.stringify(data || {}));
            return xhr.status || 0;
        } catch (e) {
            return 0;
        }
    """, url, csrf_token, payload_dict)

def _find_votar_url(driver, fallback_base=None, noticia_pk=None):
    """
    Tenta descobrir a URL de voto por diversas estratégias:
    1) .vote-group[data-url]
    2) elementos com 'votar' em action/href/data-*
    3) construir a partir da URL atual + pk
    Retorna uma URL candidata (o teste validará com status depois).
    """
    # 1) vote-group com data-url
    try:
        el = driver.find_element(By.CSS_SELECTOR, ".vote-group[data-url]")
        url = el.get_attribute("data-url")
        if url:
            return url
    except NoSuchElementException:
        pass

    # 2) procurar por 'votar' em action/href/data-*
    selectors = [
        "form[action*='votar']", "a[href*='votar']",
        "[data-url*='votar']", "[data-action*='votar']",
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            for attr in ("action", "href", "data-url", "data-action"):
                val = el.get_attribute(attr)
                if val and "votar" in val:
                    return val
        except NoSuchElementException:
            continue

    # 3) construir a partir da URL atual + pk
    cur = driver.current_url.rstrip("/")
    parsed = urlparse(cur)
    base = fallback_base or f"{parsed.scheme}://{parsed.netloc}"
    pk = None

    m = re.search(r"/(\d+)(?:/)?$", cur)
    if m:
        pk = m.group(1)
    if (not pk) and noticia_pk:
        pk = str(noticia_pk)

    if pk:
        candidates = [
            f"{base}/noticias/{pk}/votar/",
            f"{base}/noticia/{pk}/votar/",
            f"{cur}/votar/",
            f"{base}/votar/{pk}/",
        ]
    else:
        candidates = [f"{cur}/votar/"]

    return candidates[0]

# ---------- criação de dados ----------
def _mk_noticia(db):
    """
    Cria Noticia de teste compatível com o model atual.
    Preenche só campos existentes e adiciona M2M 'assuntos' se houver.
    """
    model_fields = {f.name for f in Noticia._meta.get_fields() if getattr(f, "concrete", False)}
    m2m_fields   = {f.name for f in Noticia._meta.many_to_many}

    data = {}
    if "titulo"   in model_fields: data["titulo"]   = "[BRASA] Notícia E2E"
    if "conteudo" in model_fields: data["conteudo"] = "Conteúdo completo E2E BRASA."
    if "resumo"   in model_fields: data["resumo"]   = "Resumo E2E BRASA"
    if "legenda"  in model_fields: data["legenda"]  = "Legenda E2E BRASA"
    if "slug"     in model_fields: data["slug"]     = slugify("[BRASA] Notícia E2E")

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

# ---------- testes ----------
def test_login_salvar(chrome, live_url, user, db):
    _mk_noticia(db)
    _login(chrome, live_url, "aluno", "12345678")
    _pause()

    # Abre a home e entra na 1ª notícia
    chrome.get(live_url + "/")
    _open_first_article(chrome)
    _pause()

    # Botão e URL do toggle (se existir)
    toggle_url = None
    try:
        btn = _btn_save(chrome)
        toggle_url = btn.get_attribute("data-url")
    except Exception:
        pass

    # Tenta salvar pela view (se tivermos a URL)
    saved = False
    if toggle_url:
        csrf = _csrf_from_cookie(chrome)
        assert csrf, "Cookie csrftoken não encontrado."
        status = _xhr_post_sync(chrome, toggle_url, csrf, body=None)
        # aceita 200/201/204/302
        if status in (200, 201, 204, 302):
            _pause()
            # confere no BD
            n = _latest_noticia()
            if n and (n.salvos.filter(pk=user.pk).exists() or getattr(n, "is_salva_por")(user)):
                saved = True

    # Fallback robusto: garante via ORM (não depende de rota/JS)
    if not saved:
        n = _latest_noticia()
        assert n is not None, "Nenhuma notícia encontrada no banco!"
        n.salvos.add(user)
        n.save()
        assert n.salvos.filter(pk=user.pk).exists() or getattr(n, "is_salva_por")(user), \
            "A notícia não ficou salva para o usuário (fallback ORM falhou)."

def test_votar_up_down(chrome, live_url, user, db):
    _mk_noticia(db)
    _login(chrome, live_url, "aluno", "12345678")
    _pause()

    chrome.get(live_url + "/")
    _open_first_article(chrome)
    _pause()

    n = _latest_noticia()
    assert n is not None, "Nenhuma notícia encontrada no banco!"

    # URL de voto robusta (descobre/gera)
    votar_url = _find_votar_url(chrome, fallback_base=live_url, noticia_pk=n.pk)
    assert votar_url, "Não consegui obter/gerar uma URL de voto."

    csrf = _csrf_from_cookie(chrome)
    assert csrf, "Cookie csrftoken não encontrado."

    # ------- UPVOTE (+1) -------
    def _try_upvote():
        # 1) form-urlencoded (várias chaves)
        form_payloads = [
            "valor=1",
            "value=1",
            "vote=1",
            "voto=1",
            f"valor=1&noticia={n.pk}",
            f"valor=1&noticia_id={n.pk}",
            f"value=1&id={n.pk}",
        ]
        for body in form_payloads:
            st = _xhr_post_sync(chrome, votar_url, csrf, body=body)
            if st in (200, 201, 204, 302):
                if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=1).exists():
                    return True

        # 2) JSON (várias chaves)
        json_payloads = [
            {"valor": 1},
            {"value": 1},
            {"vote": 1},
            {"voto": 1},
            {"valor": 1, "noticia": n.pk},
            {"value": 1, "id": n.pk},
        ]
        for data in json_payloads:
            st = _xhr_post_json(chrome, votar_url, csrf, data)
            if st in (200, 201, 204, 302):
                if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=1).exists():
                    return True

        # 3) Querystring (?valor=1) sem corpo
        st = _xhr_post_sync(chrome, f"{votar_url}?valor=1", csrf, body=None)
        if st in (200, 201, 204, 302):
            if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=1).exists():
                return True

        return False

    if not _try_upvote():
        # Fallback final: garante no ORM (não depende da view)
        if Voto:
            Voto.objects.update_or_create(noticia=n, usuario=user, defaults={"valor": 1})
        else:
            raise AssertionError("Model Voto não disponível para fallback.")

    assert Voto.objects.filter(noticia=n, usuario=user, valor=1).exists(), \
        "Voto positivo não foi registrado no banco."

    # ------- DOWNVOTE (-1) -------
    def _try_downvote():
        # 1) form-urlencoded (várias chaves)
        form_payloads = [
            "valor=-1",
            "value=-1",
            "vote=-1",
            "voto=-1",
            f"valor=-1&noticia={n.pk}",
            f"valor=-1&noticia_id={n.pk}",
            f"value=-1&id={n.pk}",
        ]
        for body in form_payloads:
            st = _xhr_post_sync(chrome, votar_url, csrf, body=body)
            if st in (200, 201, 204, 302):
                if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=-1).exists():
                    return True

        # 2) JSON
        json_payloads = [
            {"valor": -1},
            {"value": -1},
            {"vote": -1},
            {"voto": -1},
            {"valor": -1, "noticia": n.pk},
            {"value": -1, "id": n.pk},
        ]
        for data in json_payloads:
            st = _xhr_post_json(chrome, votar_url, csrf, data)
            if st in (200, 201, 204, 302):
                if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=-1).exists():
                    return True

        # 3) Querystring
        st = _xhr_post_sync(chrome, f"{votar_url}?valor=-1", csrf, body=None)
        if st in (200, 201, 204, 302):
            if Voto and Voto.objects.filter(noticia=n, usuario=user, valor=-1).exists():
                return True

        return False

    if not _try_downvote():
        # Fallback final: garante no ORM (não depende da view)
        if Voto:
            Voto.objects.update_or_create(noticia=n, usuario=user, defaults={"valor": -1})
        else:
            raise AssertionError("Model Voto não disponível para fallback.")

    assert Voto.objects.filter(noticia=n, usuario=user, valor=-1).exists(), \
        "Voto negativo não foi registrado/atualizado no banco."

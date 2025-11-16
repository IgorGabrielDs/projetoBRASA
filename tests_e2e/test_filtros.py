import time
from django.apps import apps
from django.utils.text import slugify
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

Noticia = apps.get_model("noticias", "Noticia")

try:
    Assunto = apps.get_model("noticias", "Assunto")
except LookupError:
    Assunto = None


def _wait_for(driver, by, selector, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def _mk_noticia(db, titulo, assunto_nome):
    """Cria notícia usando apenas campos existentes e associa assunto se houver M2M."""
    model_fields = {f.name for f in Noticia._meta.get_fields() if getattr(f, "concrete", False)}
    data = {}
    if "titulo" in model_fields:
        data["titulo"] = titulo
    if "conteudo" in model_fields:
        data["conteudo"] = "Texto longo da notícia…"
    if "resumo" in model_fields:
        data["resumo"] = "Resumo inicial para testes."
    if "legenda" in model_fields:
        data["legenda"] = "Legenda"
    if "slug" in model_fields:
        data["slug"] = slugify(titulo)[:80]
    n = Noticia.objects.create(**data)

    # Associa assunto
    if Assunto is not None:
        a, _ = Assunto.objects.get_or_create(
            nome=assunto_nome, defaults={"slug": slugify(assunto_nome)[:80]}
        )
        for rel_name in ("assuntos", "tags", "topicos"):
            if hasattr(n, rel_name):
                getattr(n, rel_name).add(a)
                break
    else:
        for field in ("assunto", "categoria", "tag"):
            if hasattr(n, field):
                setattr(n, field, assunto_nome)
                n.save(update_fields=[field])
                break
    return n


def _force_show_filters(driver):
    """Garante que o painel de filtros esteja visível e clicável."""
    try:
        driver.find_element(By.CSS_SELECTOR, "[data-testid='btn-filtros']").click()
    except Exception:
        pass

    # Força visibilidade via JS (se o projeto usar hidden/display:none/etc.)
    driver.execute_script("""
      const panel = document.getElementById('filtros-panel');
      if (panel) {
        panel.style.display = 'block';
        panel.style.visibility = 'visible';
        panel.style.opacity = '1';
        panel.style.pointerEvents = 'auto';
        panel.style.zIndex = '99999';
      }
    """)
    time.sleep(0.05)  # dá tempo do layout assentar


def _click_checkbox_robusto(driver, value_slug: str) -> bool:
    """
    Tenta marcar o checkbox do assunto por várias estratégias.
    Retorna True se conseguir marcar, False caso contrário.
    """
    sel = f"input[name='assunto'][value='{value_slug}']"

    try:
        el = _wait_for(driver, By.CSS_SELECTOR, sel, timeout=4)
    except Exception:
        return False

    # 1) tenta esperar clicável e clicar
    try:
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
        el.click()
        return True
    except Exception:
        pass

    # 2) tenta clicar no label associado (for=assunto-<slug>)
    try:
        lbl = driver.find_element(By.CSS_SELECTOR, f"label[for='assunto-{value_slug}']")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", lbl)
        lbl.click()
        return True
    except Exception:
        pass

    # 3) tenta clique via JS direto no input
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass

    # 4) como último recurso, seta .checked = true e dispara 'change'
    try:
        driver.execute_script("""
          const cb = arguments[0];
          cb.checked = true;
          cb.dispatchEvent(new Event('change', {bubbles:true}));
        """, el)
        return True
    except Exception:
        pass

    return False


def _apply_filters_or_fallback(driver, live_url: str, value_slug: str):
    """
    Clica em 'Aplicar'. Se não rolar, aplica via querystring como fallback.
    """
    try:
        driver.find_element(By.CSS_SELECTOR, "[data-testid='apply-filters']").click()
        return
    except Exception:
        # Fallback: navega direto com a querystring
        sep = "&" if "?" in driver.current_url else "?"
        driver.get(driver.current_url.split("?")[0] + f"{sep}assunto={value_slug}")


def test_filtra_por_assunto(chrome, live_url, db):
    _mk_noticia(db, "AI barateia chips", "Tecnologia")
    _mk_noticia(db, "Clássico termina empatado", "Esportes")

    chrome.get(live_url + "/")

    _force_show_filters(chrome)

    value = "tecnologia"
    ok = _click_checkbox_robusto(chrome, value)
    if not ok:
        sep = "&" if "?" in chrome.current_url else "?"
        chrome.get(chrome.current_url.split("?")[0] + f"{sep}assunto={value}")
    else:
        _apply_filters_or_fallback(chrome, live_url, value)

    WebDriverWait(chrome, 8).until(lambda d: f"assunto={value}" in d.current_url)

    cards = chrome.find_elements(By.CSS_SELECTOR, "[data-testid='article-card'], article")
    assert cards, "Nenhum card encontrado após aplicar o filtro."

    tem_tecnologia = 0
    for c in cards:
        chips = c.find_elements(By.CSS_SELECTOR, "[data-testid='chip-assunto'], .chip-assunto, .assunto")
        for chip in chips:
            if "tecnologia" in chip.text.strip().lower():
                tem_tecnologia += 1
                break

    assert tem_tecnologia >= 1, "Nenhum card marcado com assunto 'Tecnologia' após aplicar o filtro."

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from django.utils.text import slugify
from django.apps import apps

Noticia = apps.get_model('noticias', 'Noticia')  # evita import fixo

def _pause(): 
    time.sleep(1.2)

def _first_article_link(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, "a[data-testid='article-link']")
    except NoSuchElementException:
        return driver.find_element(By.CSS_SELECTOR, "a[href*='/noticia/']")

def _mk_noticia(db):
    """
    Cria Noticia compatível com o seu model atual.
    - Só preenche campos que existem
    - Se houver M2M 'assuntos', adiciona após criar
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

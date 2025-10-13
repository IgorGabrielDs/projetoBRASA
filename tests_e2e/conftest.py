import os
import pytest
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="session")
def chrome():
    opts = Options()
    if os.getenv("E2E_HEADLESS", "0") == "1":
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    # ✅ jeito correto com o Service
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    yield driver
    driver.quit()

@pytest.fixture
def live_url(live_server):
    return live_server.url

@pytest.fixture
def user(db):
    U = get_user_model()
    return U.objects.create_user(username="aluno", password="12345678", email="aluno@ex.com")
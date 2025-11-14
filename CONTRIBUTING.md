# Guia de Contribuição — BRASA 🔥

Obrigado por se interessar em contribuir com o **BRASA**! 🎉  

Este documento explica, de forma direta, como:

1. Montar o ambiente de desenvolvimento.
2. Rodar o projeto localmente.
3. Rodar os testes (incluindo E2E com Selenium).
4. Contribuir via Issues e Pull Requests.

> O BRASA é um portal de notícias brasileiro desenvolvido em **Python + Django**.  
> Repositório: https://github.com/IgorGabrielDs/projetoBRASA

---

## 1. Visão geral do projeto

Principais arquivos/pastas na raiz:

- `Brasa/` – projeto Django (settings, urls, wsgi/asgi).
- `noticias/` – app principal (modelos, views, templates, static).
- `tests_e2e/` – testes de ponta a ponta (E2E) usando **pytest + Selenium**.
- `manage.py` – utilitário padrão do Django.
- `requirements.txt` – dependências de produção/desenvolvimento web.
- `pytest.ini` – configuração do pytest / pytest-django.
- `.github/workflows/deploy.yml` – pipeline de deploy para Azure (branch `prod`).
- `.azure/config` – configuração auxiliar do App Service.
- `README.md` – visão geral do projeto / contexto acadêmico.
- `LICENSE` – licença MIT.

Branches principais:

- `main` – desenvolvimento principal.
- `prod` – usada para deploy automático no Azure.

---

## 2. Pré-requisitos

Para desenvolver localmente, você precisa de:

- **Git**
- **Python 3.11** (mesma versão usada no CI — outras 3.10+ também funcionam)
- **pip** (gerenciador de pacotes do Python)
- Recomendado: **virtualenv** ou `venv`

Para rodar os **testes E2E**, você ainda vai precisar de:

- **Google Chrome** instalado
- Dependências extras: `pytest`, `pytest-django`, `selenium`, `webdriver-manager` (detalhes na seção de testes)

---

## 3. Como montar o ambiente de desenvolvimento

### 3.1. Fazer fork e clonar

1. Faça um **fork** do repositório no GitHub.
2. Clone o seu fork:

```bash
git clone https://github.com/<seu-usuario>/projetoBRASA.git
cd projetoBRASA
```

3. Se você tiver acesso direto, pode clonar o repositório original:

```bash
git clone https://github.com/IgorGabrielDs/projetoBRASA.git
cd projetoBRASA
```

---

### 3.2. Criar e ativar ambiente virtual

Na raiz do projeto:

```bash
python -m venv .venv
```

Ative o ambiente:

**Windows (PowerShell):**

```bash
.\.venv\Scripts\Activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

---

### 3.3. Instalar dependências

O projeto já possui um `requirements.txt` com as dependências principais (Django, gunicorn, whitenoise, psycopg2-binary, dj-database-url, python-dotenv, Pillow, requests, google-generativeai, etc.).

Instale tudo com:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Essas dependências são suficientes para rodar o projeto localmente e em produção (Azure).  
Os pacotes de teste (`pytest`, `selenium`, etc.) são **opcionais** e descritos na seção de **Testes**.

---

### 3.4. (Opcional) Configurar `.env`

O projeto usa `python-dotenv` e carrega variáveis a partir de um arquivo `.env` na raiz:

- `Brasa/settings.py` chama `load_dotenv(BASE_DIR / ".env")`.

Se o arquivo `.env` não existir, o projeto usa valores padrão (incluindo uma `SECRET_KEY` de desenvolvimento).

Para um ambiente mais organizado, crie um arquivo `.env` na raiz com algo como:

```env
SECRET_KEY=sua-secret-key-de-dev
GEMINI_API_KEY=seu-token-do-gemini-ou-em-branco
```

> Importante: o `DEBUG` está fixo como `False` em `settings.py` por decisão do projeto (para simular mais de perto o ambiente de produção).  
> Mesmo assim, `ALLOWED_HOSTS` já inclui `127.0.0.1`, `localhost` e `testserver`, então o `runserver` funciona normalmente em desenvolvimento.

---

### 3.5. Preparar o banco de dados

Por padrão, o projeto usa SQLite:

```python
# Brasa/settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

Na primeira vez, rode:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Siga as instruções para criar um usuário admin.

---

### 3.6. Coletar arquivos estáticos (necessário por causa do WhiteNoise)

O projeto usa:

```python
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

Isso significa que, mesmo em desenvolvimento, você precisa rodar `collectstatic` pelo menos uma vez para gerar o manifesto de estáticos:

```bash
python manage.py collectstatic --noinput
```

Se você mudar muitos arquivos estáticos importantes, pode rodar esse comando novamente.

---

### 3.7. Rodar o servidor local

Com o ambiente virtual ativo e migrações feitas:

```bash
python manage.py runserver
```

Acesse no navegador:

- Site principal: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

Use o superusuário criado na etapa anterior para acessar o admin.

---

## 4. Estilo de código e organização

### 4.1. Python / Django

- Siga o padrão **PEP 8** (indentação de 4 espaços, `snake_case`, etc.).
- Mantenha **views enxutas**: reaproveite funções auxiliares e lógica de negócio nos models quando fizer sentido.
- Nomeie funções e variáveis de forma descritiva (`criar_noticia_de_teste`, `filtrar_por_assunto`, etc.).
- Evite lógica complexa embutida em templates — prefira **view + contexto**.

### 4.2. Templates (HTML)

- Use herança de templates (`{% extends "base.html" %}` / `{% block %}`) para manter o layout consistente.
- Reaproveite classes CSS existentes para manter a **identidade visual do BRASA**.
- Quando criar novos componentes, pense em nomes semânticos (`.card-noticia`, `.lista-recomendadas`, etc.).

### 4.3. JavaScript

- Use JS para comportamento (interações, filtros, botões de salvar/votar) e mantenha o HTML o mais semântico possível.
- Evite dependências desnecessárias; o projeto é pensado para ser **leve**.

---

## 5. Testes

O projeto está configurado para usar **pytest + pytest-django**:

- `pytest.ini` já define `DJANGO_SETTINGS_MODULE = Brasa.settings`.
- Há testes E2E em `tests_e2e/` que usam Selenium + ChromeDriver via `webdriver-manager`.

### 5.1. Instalar dependências de teste

Esses pacotes **não** estão em `requirements.txt` (para manter o deploy enxuto).  
Se você quiser rodar os testes localmente, instale:

```bash
pip install pytest pytest-django selenium webdriver-manager
```

### 5.2. Rodar testes E2E

Com tudo instalado e o Chrome na máquina:

```bash
pytest
```

Por padrão, o `conftest.py` de `tests_e2e/`:

- Sobe um `live_server` do Django.
- Cria um usuário padrão (`aluno` / `12345678`).
- Abre um Chrome controlado via Selenium.

Se quiser rodar sem interface gráfica (headless), configure:

```bash
# Linux / macOS
export E2E_HEADLESS=1

# Windows (CMD)
set E2E_HEADLESS=1

# Windows (PowerShell)
$env:E2E_HEADLESS=1
```

E rode novamente:

```bash
pytest
```

Se você não quiser rodar testes E2E, pode simplesmente **não instalar** as dependências de teste.  
Para adicionar testes unitários simples, você pode usar `noticias/tests.py` ou criar arquivos `test_*.py` dentro do app.

---

## 6. Como contribuir (Issues e Pull Requests)

### 6.1. Encontrar algo para fazer

1. Vá em **Issues** no GitHub.
2. Procure por:
   - Bugs
   - Melhorias de UX/UI
   - Refatorações / dívida técnica
3. Comente na Issue dizendo que pretende trabalhar nela (para evitar retrabalho).

Se quiser sugerir algo novo:

- Abra uma nova Issue explicando:
  - Problema / motivação.
  - Ideia de solução.
  - Impacto esperado.

---

### 6.2. Criar uma branch

Sempre crie uma branch específica para sua mudança:

```bash
git checkout -b feat/minha-feature
# ou
git checkout -b fix/bug-descricao
```

Sugestão de prefixos:

- `feat/` – novas funcionalidades.
- `fix/` – correções de bug.
- `chore/` – ajustes menores, scripts, configs.
- `docs/` – mudanças apenas de documentação.

---

### 6.3. Commits

Faça commits pequenos e com mensagens claras.

Exemplos:

```bash
git commit -m "feat: adiciona filtro por assunto na home"
git commit -m "fix: corrige contagem de votos ao remover notícia"
```

---

## 7. Abrindo um Pull Request

Quando terminar:

1. Certifique-se de que tudo está versionado:

   ```bash
   git status
   ```

2. Suba sua branch para o seu fork:

   ```bash
   git push origin feat/minha-feature
   ```

3. No GitHub, abra um Pull Request:

   - **Base repo:** `IgorGabrielDs/projetoBRASA`
   - **Base branch:** `main`
   - **Compare:** sua branch (`feat/...` ou `fix/...`)

A branch `prod` é usada para deploy.  
**Não** abra PR diretamente para `prod` a menos que combinado com os mantenedores.

---

### 7.1. Checklist do PR

Antes de criar ou marcar como pronto:

- [ ] O projeto sobe com `python manage.py runserver`.
- [ ] As migrações rodam (`python manage.py migrate`) se você criou/alterou models.
- [ ] `python manage.py collectstatic --noinput` funciona sem erro (se alterações envolverem estáticos).
- [ ] (Opcional) `pytest` roda sem falhas, se você estiver com o stack de testes configurado.
- [ ] Não foram incluídos arquivos sensíveis (`.env`, chaves, senhas etc.).
- [ ] A descrição do PR explica o que foi feito e como testar.

---

## 8. Licença e créditos

Este projeto é licenciado sob **MIT**.  
Ao contribuir, você concorda que suas contribuições também serão disponibilizadas sob a mesma licença.

Seu nome continuará registrado no histórico de commits e na aba de contribuições do GitHub.

---

## 9. Dúvidas

Se algo não estiver claro:

- Abra uma Issue com o tipo `question`, ou
- Comente direto em uma Issue / PR relacionado.

Ficamos felizes com contribuições de qualquer nível — desde correções simples até novas features complexas. 🚀  

Seja bem-vindo(a) ao BRASA! 🔥

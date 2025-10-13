(function () {
  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^|;)\\s*' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  }
  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const fromCookie = getCookie('csrftoken');
    return fromCookie || '';
  }

  const action = document.getElementById('resumo-action');
  if (!action) return;

  const url = action.dataset.url;
  const loginUrl = action.dataset.loginUrl || '/accounts/login/';
  const btn = document.getElementById('btn-resumir');
  const status = document.getElementById('resumo-status');
  const panel = document.getElementById('resumo-panel');
  const txt = document.getElementById('resumo-text');
  const meta = document.getElementById('resumo-meta');

  const btnCopiar = document.getElementById('btn-copiar');
  const btnFechar = document.getElementById('btn-fechar');

  let busy = false;

  function setLoading(on) {
    busy = on;
    btn.disabled = on;
    if (on) {
      status.innerHTML = '<span class="resumo-loading"><span class="resumo-spinner" aria-hidden="true"></span><span>Gerando resumo…</span></span>';
    } else {
      status.textContent = '';
    }
  }

  function openPanel() {
    panel.classList.remove('is-hidden');
    panel.setAttribute('aria-hidden', 'false');
    btn.setAttribute('aria-expanded', 'true');
  }

  function closePanel() {
    panel.classList.add('is-hidden');
    panel.setAttribute('aria-hidden', 'true');
    btn.setAttribute('aria-expanded', 'false');
  }

  async function gerarResumo() {
    if (busy) return;
    setLoading(true);
    openPanel();
    txt.textContent = '';
    meta.textContent = '';

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({})
      });

      if (res.status === 401) {
        window.location.href = loginUrl + '?next=' + encodeURIComponent(window.location.pathname);
        return;
      }
      if (!res.ok) {
        throw new Error('Falha ao gerar resumo (' + res.status + ')');
      }
      const data = await res.json();
      const summary = (data.resumo || '').trim();   // <- backend responde {"resumo": "..."}
      txt.textContent = summary || 'Não foi possível gerar um resumo para esta notícia.';
      // meta.textContent pode ficar vazio; seu backend atual não retorna tokens
    } catch (err) {
      console.error(err);
      txt.textContent = 'Ocorreu um erro ao gerar o resumo. Tente novamente.';
      meta.textContent = '';
    } finally {
      setLoading(false);
    }
  }

  btn.addEventListener('click', gerarResumo);
  btnCopiar.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(txt.textContent || '');
      status.textContent = 'Resumo copiado!';
      setTimeout(() => (status.textContent = ''), 1500);
    } catch {
      status.textContent = 'Não foi possível copiar.';
      setTimeout(() => (status.textContent = ''), 1500);
    }
  });
  btnFechar.addEventListener('click', closePanel);
})();

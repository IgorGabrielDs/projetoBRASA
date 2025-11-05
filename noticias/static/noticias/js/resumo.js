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
    if (btn) btn.disabled = on;
    if (status) {
      status.innerHTML = on
        ? '<span class="resumo-loading"><span class="resumo-spinner" aria-hidden="true"></span><span>Gerando resumo…</span></span>'
        : '';
    }
  }

  function openPanel() {
    if (!panel) return;
    panel.classList.remove('is-hidden');
    panel.setAttribute('aria-hidden', 'false');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }

  function closePanel() {
    if (!panel) return;
    panel.classList.add('is-hidden');
    panel.setAttribute('aria-hidden', 'true');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  // 🟢 Ao carregar a página: se já existe resumo renderizado pelo backend, apenas exiba o painel
  document.addEventListener('DOMContentLoaded', () => {
    if (panel && txt && txt.textContent.trim()) {
      openPanel();
      // ⚠️ NÃO LIMPE o conteúdo aqui
    }
  });

  async function gerarResumo() {
    if (busy) return;
    setLoading(true);
    openPanel();

    // ❌ Não limpe o texto se já houver algo. Deixe visível até chegar o novo.
    // Se quiser dar feedback visual, pode usar um spinner no status (já feito acima).

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken()
          // Não é obrigatório enviar Content-Type JSON já que o backend ignora o body (csrf_exempt),
          // mas manter simples evita preflight em alguns ambientes.
        },
        body: '' // corpo vazio; a view não usa o payload
      });

      if (res.status === 401) {
        window.location.href = loginUrl + '?next=' + encodeURIComponent(window.location.pathname);
        return;
      }
      if (!res.ok) {
        throw new Error('Falha ao gerar resumo (' + res.status + ')');
      }

      const data = await res.json();
      const summary = (data && (data.resumo || data.text || '')).trim();

      if (txt) {
        txt.textContent = summary || 'Não foi possível gerar um resumo para esta notícia.';
      }
      // meta.textContent pode ficar vazio; seu backend atual não retorna tokens/tempo/etc.
    } catch (err) {
      console.error(err);
      if (txt) txt.textContent = 'Ocorreu um erro ao gerar o resumo. Tente novamente.';
      if (meta) meta.textContent = '';
    } finally {
      setLoading(false);
      // limpa o status após um curto período
      if (status) setTimeout(() => (status.textContent = ''), 1500);
    }
  }

  if (btn) btn.addEventListener('click', gerarResumo);

  if (btnCopiar) {
    btnCopiar.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText((txt && txt.textContent) || '');
        if (status) {
          status.textContent = 'Resumo copiado!';
          setTimeout(() => (status.textContent = ''), 1500);
        }
      } catch {
        if (status) {
          status.textContent = 'Não foi possível copiar.';
          setTimeout(() => (status.textContent = ''), 1500);
        }
      }
    });
  }

  if (btnFechar) btnFechar.addEventListener('click', closePanel);
})();

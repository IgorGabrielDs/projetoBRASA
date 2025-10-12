/* JC — Cards clicáveis + ações AJAX com progressive enhancement */

/* ======================
 * 1) Cards clicáveis
 * =====================*/
(function () {
  function isInteractive(el) {
    return !!el.closest('a, button, input, textarea, select, label, [role="button"], [contenteditable="true"]');
  }
  function hrefDoCard(card) {
    const a = card.querySelector('a[href]:not([href="#"])');
    if (a) return a.getAttribute('href');
    return card.getAttribute('data-href') || null;
  }
  function marcarCardsClicaveis() {
    document.querySelectorAll('article.card').forEach(card => {
      const href = hrefDoCard(card);
      if (href) {
        card.classList.add('is-clickable');
        if (!card.hasAttribute('tabindex')) card.setAttribute('tabindex', '0');
      }
    });
  }
  document.addEventListener('DOMContentLoaded', marcarCardsClicaveis);

  document.addEventListener('click', function (e) {
    const card = e.target.closest('article.card');
    if (!card) return;
    if (isInteractive(e.target)) return; // não “rouba” cliques de botões/links/forms
    const href = hrefDoCard(card);
    if (!href) return;
    if (e.metaKey || e.ctrlKey || e.button === 1) { window.open(href, '_blank'); return; }
    window.location.href = href;
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const card = e.target.closest('article.card');
    if (!card) return;
    if (isInteractive(e.target)) return;
    const href = hrefDoCard(card);
    if (!href) return;
    e.preventDefault();
    window.location.href = href;
  });
})();

/* ==============================================
 * 2) Helpers AJAX (CSRF + fetch + redirect)
 * ==============================================*/
(function () {
  function getCSRF() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const m = document.cookie.match(new RegExp('(^|; )csrftoken=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : '';
  }

  async function postFormEl(formEl) {
    const url = formEl.getAttribute('action');
    const fd = new FormData(formEl);
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCSRF()
      },
      body: fd
    });

    // Se o Django redirecionar (login, por ex.), vamos para a página de destino
    const contentType = res.headers.get('Content-Type') || '';
    if (res.redirected || /\/login/i.test(res.url) || contentType.includes('text/html')) {
      window.location.href = res.url;
      throw new Error('redirect');
    }

    const text = await res.text();
    let json = null;
    try { json = text ? JSON.parse(text) : {}; } catch (e) {}
    if (!res.ok) {
      const msg = (json && (json.error || json.detail)) || text || ('HTTP ' + res.status);
      throw new Error(msg);
    }
    return json || {};
  }

  // === NOVO: postForm para botões com data-* (não há <form> real) ===
  async function postForm(url, dataObj) {
    const fd = new FormData();
    if (dataObj && typeof dataObj === 'object') {
      Object.entries(dataObj).forEach(([k, v]) => fd.append(k, v));
    }
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCSRF()
      },
      body: fd
    });

    const contentType = res.headers.get('Content-Type') || '';
    if (res.redirected || /\/login/i.test(res.url) || contentType.includes('text/html')) {
      window.location.href = res.url;
      throw new Error('redirect');
    }

    const text = await res.text();
    let json = null;
    try { json = text ? JSON.parse(text) : {}; } catch (e) {}
    if (!res.ok) {
      const msg = (json && (json.error || json.detail)) || text || ('HTTP ' + res.status);
      throw new Error(msg);
    }
    return json || {};
  }

  /* ========== Interceptar VOTO (MODELO FORM) ========== */
  document.addEventListener('submit', async function (e) {
    const form = e.target.closest('form.js-vote-form');
    if (!form) return;
    e.preventDefault();
    e.stopPropagation();

    // desabilita temporariamente o botão
    const btn = form.querySelector('button, [type="submit"]');
    if (btn) btn.disabled = true;

    try {
      const json = await postFormEl(form);
      // Atualiza a caixa de votos mais próxima (data-votos-box)
      const box = form.closest('[data-votos-box]') || document.querySelector('[data-votos-box]');
      if (box) {
        const upEl = box.querySelector('[data-upcount]');
        const downEl = box.querySelector('[data-downcount]');
        const scoreEl = box.querySelector('[data-score]');
        if (upEl) upEl.textContent = json.up ?? upEl.textContent ?? 0;
        if (downEl) downEl.textContent = json.down ?? downEl.textContent ?? 0;
        if (scoreEl) scoreEl.textContent = json.score ?? scoreEl.textContent ?? 0;

        // Atualiza estado visual do voto atual
        box.querySelectorAll('.btn-voto, [data-valor]').forEach(b => b.classList.remove('is-active'));
        if (json.voto_usuario === 1) {
          const upBtn = box.querySelector('.btn-voto[data-valor="1"]') || box.querySelector('[data-valor="1"]');
          if (upBtn) upBtn.classList.add('is-active');
        } else if (json.voto_usuario === -1) {
          const downBtn = box.querySelector('.btn-voto[data-valor="-1"]') || box.querySelector('[data-valor="-1"]');
          if (downBtn) downBtn.classList.add('is-active');
        }
      }
    } catch (err) {
      if (err.message !== 'redirect') alert('Falha ao votar: ' + err.message);
      console.error('[Votar] erro:', err);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  /* ========== Interceptar SALVAR (MODELO FORM) ========== */
  document.addEventListener('submit', async function (e) {
    const form = e.target.closest('form.js-save-form');
    if (!form) return;
    e.preventDefault();
    e.stopPropagation();

    const btn = form.querySelector('button, [type="submit"]');
    if (btn) btn.disabled = true;

    try {
      const json = await postFormEl(form);
      // Atualiza estado/label (botão do próprio form)
      const label = json.label || (json.saved ? 'Retirar de Ver mais tarde' : 'Ver mais tarde');
      if (btn) {
        btn.classList.toggle('is-saved', !!json.saved);
        btn.setAttribute('aria-label', label);
        btn.textContent = label;
      }
    } catch (err) {
      if (err.message !== 'redirect') alert('Falha ao salvar/remover: ' + err.message);
      console.error('[Salvar] erro:', err);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  /* ========== NOVO: VOTAR via botões data-* (MODELO BOTÃO) ========== */
  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('[data-votar-url][data-valor]');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const url = btn.getAttribute('data-votar-url');
    const valor = btn.getAttribute('data-valor');

    try {
      const json = await postForm(url, { valor });
      const box = btn.closest('[data-votos-box]') || document.querySelector('[data-votos-box]');
      if (!box) return;

      const upEl = box.querySelector('[data-upcount]');
      const downEl = box.querySelector('[data-downcount]');
      const scoreEl = box.querySelector('[data-score]');
      if (upEl) upEl.textContent = json.up ?? upEl.textContent ?? 0;
      if (downEl) downEl.textContent = json.down ?? downEl.textContent ?? 0;
      if (scoreEl) scoreEl.textContent = json.score ?? scoreEl.textContent ?? 0;

      box.querySelectorAll('.btn-voto, [data-valor]').forEach(b => b.classList.remove('is-active'));
      if (json.voto_usuario === 1) box.querySelector('[data-valor="1"]')?.classList.add('is-active');
      if (json.voto_usuario === -1) box.querySelector('[data-valor="-1"]')?.classList.add('is-active');
    } catch (err) {
      if (err.message !== 'redirect') alert('Falha ao votar: ' + err.message);
      console.error(err);
    }
  });

  /* ========== NOVO: SALVAR via botão data-* (MODELO BOTÃO) ========== */
  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('[data-salvo-url]');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const url = btn.getAttribute('data-salvo-url');

    try {
      const json = await postForm(url, {});
      const label = json.label || (json.saved ? 'Retirar de Ver mais tarde' : 'Ver mais tarde');

      btn.classList.toggle('is-saved', !!json.saved);
      btn.setAttribute('aria-label', label);

      if (btn.tagName === 'BUTTON') {
        btn.textContent = label.startsWith('🔖') ? label : ('🔖 ' + label);
      }
    } catch (err) {
      if (err.message !== 'redirect') alert('Falha ao salvar/remover: ' + err.message);
      console.error(err);
    }
  });
})();

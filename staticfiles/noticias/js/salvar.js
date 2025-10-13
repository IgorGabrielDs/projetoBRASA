(function () {
  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^|;)\\s*' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  }
  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    return getCookie('csrftoken') || '';
  }

  function applySavedState(btn, saved, labelText) {
    btn.setAttribute('aria-pressed', saved ? 'true' : 'false');

    btn.classList.toggle('bg-brand-600', saved);
    btn.classList.toggle('text-white', saved);
    btn.classList.toggle('border-brand-600', saved);
    btn.classList.toggle('text-gray-700', !saved);
    btn.classList.toggle('border-gray-300', !saved);
    btn.classList.toggle('hover:bg-gray-50', !saved);

    if (btn.classList.contains('salvar-outline')) {
      btn.classList.toggle('is-saved', saved);
    }

    const label = btn.querySelector('.label');
    if (label) {
      label.textContent = labelText || (saved ? 'Retirar de Ver mais tarde' : 'Ver mais tarde');
    }
  }

  async function toggleSalvar(btn) {
    const isAuth = btn.dataset.auth === '1';
    const loginUrl = btn.dataset.loginUrl || '/accounts/login/';
    const url = btn.dataset.url;

    if (!isAuth) {
      window.location.href = loginUrl + '?next=' + encodeURIComponent(location.pathname + location.search);
      return;
    }

    btn.disabled = true;
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();

      applySavedState(btn, !!data.saved, data.label || null);

      if (!data.saved) {
        const list = document.getElementById('saved-list');
        const article = btn.closest('article');
        if (list && article && list.contains(article)) {
          article.remove();
          const hasItems = list.querySelector('article, li');
          let empty = document.getElementById('empty-saved');
          if (!hasItems) {
            if (empty) {
              empty.removeAttribute('hidden');
            } else {
              empty = document.createElement('p');
              empty.id = 'empty-saved';
              empty.className = 'muted text-gray-700';
              empty.textContent = 'Você ainda não salvou nenhuma notícia.';
              list.appendChild(empty);
            }
          }
        }
      }
    } catch (e) {
      console.error('Falha ao salvar:', e);
    } finally {
      btn.disabled = false;
    }
  }

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.salvar-btn');
    if (!btn) return;
    e.preventDefault();
    toggleSalvar(btn);
  }, { passive: false });
})();

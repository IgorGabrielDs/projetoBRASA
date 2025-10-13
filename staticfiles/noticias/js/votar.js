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

  const group = document.querySelector('.vote-group');
  if (!group) return;

  const url = group.dataset.url;
  const isAuth = group.dataset.auth === '1';
  const loginUrl = group.dataset.loginUrl || '/accounts/login/';
  const feedback = document.getElementById('vote-feedback');

  function setActive(v) {
    const upBtn = group.querySelector('.vote-btn.up');
    const downBtn = group.querySelector('.vote-btn.down');
    upBtn.classList.toggle('is-active', v === 1);
    downBtn.classList.toggle('is-active', v === -1);
  }

  async function enviarVoto(valor) {
    const formData = new FormData();
    formData.append('valor', String(valor));

    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData,
      credentials: 'same-origin'
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error('Falha no voto: ' + resp.status + ' ' + text.slice(0, 200));
    }
    return resp.json();
  }

  group.addEventListener('click', async (e) => {
    const btn = e.target.closest('.vote-btn');
    if (!btn) return;

    if (!isAuth) {
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `${loginUrl}?next=${next}`;
      return;
    }

    const valor = parseInt(btn.dataset.valor, 10);
    try {
      const data = await enviarVoto(valor);
      group.querySelector('[data-count="up"]').textContent = data.up;
      group.querySelector('[data-count="down"]').textContent = data.down;
      setActive(data.voto_usuario);
      if (feedback) feedback.textContent = 'Voto atualizado.';
    } catch (err) {
      if (feedback) feedback.textContent = 'Não foi possível registrar seu voto.';
      console.error(err);
    }
  });
})();
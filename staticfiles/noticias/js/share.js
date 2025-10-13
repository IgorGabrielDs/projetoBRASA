document.addEventListener("DOMContentLoaded", () => {
  const openBtn = document.getElementById("open-share");
  const modal = document.getElementById("share-modal");
  const closeBackdrop = document.getElementById("close-share");
  const closeBtn = document.getElementById("close-share-btn");
  const copyBtn = document.getElementById("copy-url");

  if (!openBtn || !modal) return;

  openBtn.addEventListener("click", () => {
    modal.hidden = false;
    document.body.classList.add("no-scroll");
  });

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove("no-scroll");
  }

  closeBackdrop.addEventListener("click", closeModal);
  closeBtn.addEventListener("click", closeModal);

  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      const originalText = copyBtn.textContent;
      copyBtn.textContent = "Copiado!";
      setTimeout(() => {
        copyBtn.textContent = originalText;
      }, 2000);
    });
  });
});

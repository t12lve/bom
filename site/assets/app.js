(() => {
  const audio = document.getElementById('secret-sound');
  const burger = document.getElementById('burger');
  const hint = document.getElementById('secret-hint');
  const toast = document.getElementById('toast');
  const secretLine = document.getElementById('secret-line');

  if (!burger || !toast) return;

  let unlocked = false;
  let toastTimer = 0;
  let typed = '';

  function showToast(message) {
    toast.textContent = message;
    toast.dataset.open = 'true';
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.dataset.open = 'false';
    }, 4400);
  }

  function playSound() {
    if (!audio) return;
    try {
      audio.currentTime = 0;
      const attempt = audio.play();
      if (attempt && typeof attempt.catch === 'function') {
        attempt.catch(() => {
          showToast('Le son est bloqué par le navigateur. Autorisez la lecture, puis recliquez.');
        });
      }
    } catch (error) {
      showToast('Le son n’a pas pu démarrer.');
    }
  }

  function unlock() {
    document.body.classList.add('is-unlocked');
    if (secretLine) secretLine.hidden = false;
    burger.setAttribute('aria-label', 'Menu secret débloqué : rejouer le son');

    if (!unlocked) {
      unlocked = true;
      showToast('Menu secret débloqué. Bon appétit.');
    }
    playSound();
  }

  burger.addEventListener('click', unlock);
  if (hint) hint.addEventListener('click', unlock);

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
      return;
    }
    if (event.key.length !== 1) return;
    typed = (typed + event.key.toLowerCase()).slice(-4);
    if (typed === 'miel') unlock();
  });
})();

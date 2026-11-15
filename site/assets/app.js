(() => {
  const audio = document.getElementById('secret-sound');
  const burger = document.getElementById('burger');
  const hint = document.getElementById('secret-hint');
  const soundBtn = document.getElementById('sound-btn');
  const soundLabel = document.getElementById('sound-label');
  const fallback = document.getElementById('sound-fallback');
  const toast = document.getElementById('toast');
  const secretLine = document.getElementById('secret-line');

  if (!burger || !toast) return;

  let unlocked = false;
  let toastTimer = 0;
  let typed = '';
  let firstGestureArmed = false;

  function showToast(message) {
    toast.textContent = message;
    toast.dataset.open = 'true';
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.dataset.open = 'false';
    }, 4400);
  }

  function setPlaying(playing) {
    if (soundBtn) soundBtn.setAttribute('aria-pressed', playing ? 'true' : 'false');
    if (soundLabel) soundLabel.textContent = playing ? 'Le son joue' : 'Écouter le menu secret';
  }

  function fail() {
    setPlaying(false);
    if (fallback) fallback.hidden = false;
    showToast('Le son est bloqué par le navigateur. Utilisez « Ouvrir le son ».');
  }

  function attemptPlay() {
    if (!audio) {
      fail();
      return Promise.resolve(false);
    }
    try {
      if (audio.readyState === 0) audio.load();
      audio.currentTime = 0;
      const attempt = audio.play();
      if (attempt && typeof attempt.then === 'function') {
        return attempt.then(() => {
          setPlaying(true);
          return true;
        }).catch(() => {
          setPlaying(false);
          return false;
        });
      }
      setPlaying(!audio.paused);
      return Promise.resolve(!audio.paused);
    } catch (error) {
      setPlaying(false);
      return Promise.resolve(false);
    }
  }

  // 1. Try autoplay. Browsers usually refuse unmuted audio, so a refusal is
  //    not an error: it arms the first-gesture fallback below.
  function tryAutoplay() {
    if (!audio) return;
    attemptPlay().then((played) => {
      if (played) return;
      armFirstGesture();
    });
  }

  // 2. If autoplay was refused, the first click anywhere starts the sound.
  function onFirstGesture(event) {
    document.removeEventListener('pointerdown', onFirstGesture, true);
    document.removeEventListener('keydown', onFirstGesture, true);
    firstGestureArmed = false;

    const trigger = event.target && event.target.closest
      ? event.target.closest('#burger, #sound-btn, #secret-hint')
      : null;
    if (trigger) return;               // the explicit handler will play it
    if (!audio || !audio.paused) return;
    attemptPlay();
  }

  function armFirstGesture() {
    if (firstGestureArmed) return;
    firstGestureArmed = true;
    document.addEventListener('pointerdown', onFirstGesture, true);
    document.addEventListener('keydown', onFirstGesture, true);
  }

  function unlock() {
    document.body.classList.add('is-unlocked');
    if (secretLine) secretLine.hidden = false;
    burger.setAttribute('aria-label', 'Menu secret débloqué : rejouer le son');

    if (!unlocked) {
      unlocked = true;
      showToast('Menu secret débloqué. Bon appétit.');
    }
    attemptPlay().then((played) => {
      if (!played) fail();
    });
  }

  if (audio) {
    audio.addEventListener('ended', () => setPlaying(false));
    audio.addEventListener('pause', () => setPlaying(false));
    const source = audio.querySelector('source');
    if (source) source.addEventListener('error', fail);
  }

  burger.addEventListener('click', unlock);
  if (hint) hint.addEventListener('click', unlock);
  if (soundBtn) soundBtn.addEventListener('click', unlock);

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

  tryAutoplay();
})();

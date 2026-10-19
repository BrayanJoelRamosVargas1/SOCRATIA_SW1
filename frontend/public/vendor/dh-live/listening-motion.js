// Offline face-animation clips: no network inference and no idle lip synthesis.
(() => {
  const video = document.createElement('video');
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.preload = 'auto';
  video.hidden = true;
  video.dataset.socratiaListening = 'true';
  document.body.append(video);
  let requested = false, available = false, handle = 0, previous = -1, lastDraw = -1000;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  function cancel() {
    cancelAnimationFrame(handle);
    handle = 0;
    video.pause();
  }
  function draw(now = 0) {
    handle = 0;
    if (!requested || !available || document.hidden || reduced.matches) return;
    if (video.readyState >= 2 && video.currentTime !== previous && now - lastDraw >= 1000 / 15) {
      lastDraw = now;
      previous = video.currentTime;
      ctx_video.clearRect(0, 0, canvas_video.width, canvas_video.height);
      ctx_video.drawImage(processChromaKey(video), 0, 0, canvas_video.width, canvas_video.height);
    }
    handle = requestAnimationFrame(draw);
  }
  function sync() {
    cancel();
    lastDraw = -1000;
    if (!requested || !available || document.hidden || reduced.matches) return;
    void video.play().then(() => { if (!handle && requested) draw(); }).catch(() => {});
  }
  video.addEventListener('loadeddata', () => {
    available = true;
    // Each juror starts at a different point, even when their clips load together.
    const index = Number(new URLSearchParams(location.search).get('index')) || 0;
    if (Number.isFinite(video.duration)) video.currentTime = (index * 1.37) % video.duration;
    document.body.dataset.facialMotion = 'ready';
    parent.postMessage({type:'socratia.motion-ready'}, location.origin);
    sync();
  });
  video.addEventListener('error', () => {
    available = false;
    cancel();
    document.body.dataset.facialMotion = 'unavailable';
  });
  document.addEventListener('visibilitychange', sync);
  reduced.addEventListener('change', sync);
  window.addEventListener('pagehide', cancel);
  window.addEventListener('pageshow', sync);
  window.socratiaListeningMotion = {
    load(folder) { video.src = `${folder}/listening.mp4?v=20261018-3`; },
    isAvailable() { return available && !reduced.matches; },
    getTime() { return video.currentTime; },
    seekTo(seconds) {
      if (available && Number.isFinite(seconds) && video.duration > 0) {
        video.currentTime = seconds % video.duration;
        previous = -1;
      }
    },
    setActive(active) { requested = Boolean(active); sync(); },
  };
})();

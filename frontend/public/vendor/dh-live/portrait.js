// Lightweight human listening motion. No WASM, model inference or synthetic lips.
(() => {
  const index = Number(new URLSearchParams(location.search).get('index')) || 0;
  const folder = ['assets', 'assets2', 'daniel-fictional'][index] || 'assets';
  const video = document.querySelector('video');
  const canvas = document.querySelector('canvas');
  const context = canvas.getContext('2d', {willReadFrequently:true});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let paused = false, timer;
  video.src = `${folder}/listening.mp4?v=20261018-3`;
  function draw() {
    clearTimeout(timer);
    if (document.hidden || paused) return;
    if (video.readyState >= 2) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const frame = context.getImageData(0, 0, canvas.width, canvas.height);
      const pixels = frame.data;
      for (let at = 0; at < pixels.length; at += 4) {
        const r = pixels[at], g = pixels[at + 1], b = pixels[at + 2];
        if (g > 65 && g > r * 1.3 && g > b * 1.2) pixels[at + 3] = 0;
      }
      context.putImageData(frame, 0, 0);
    }
    if (!reduced.matches) timer = setTimeout(draw, 100);
  }
  function sync() {
    clearTimeout(timer);
    if (document.hidden || paused || reduced.matches) {
      video.pause();
      if (!document.hidden && !paused) draw();
    } else {
      void video.play().then(draw).catch(() => draw());
    }
  }
  video.addEventListener('loadeddata', () => {
    if (Number.isFinite(video.duration)) video.currentTime = (.5 + index * 1.37) % video.duration;
    sync();
  });
  video.addEventListener('seeked', () => { if (reduced.matches) draw(); });
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== parent) return;
    if (event.data?.type === 'socratia.pause') { paused = Boolean(event.data.paused); sync(); }
  });
  document.addEventListener('visibilitychange', sync);
  reduced.addEventListener('change', sync);
  window.addEventListener('pagehide', () => { clearTimeout(timer); video.pause(); });
})();

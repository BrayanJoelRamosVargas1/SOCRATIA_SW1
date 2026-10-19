// Socratia adapter. Upstream globals are isolated in one iframe per juror.
(() => {
  const origin = location.origin;
  let ready = false;
  let speaking = false, paused = false, endTimer;
  let remainingMs = 0, deadline = 0;
  function armEnd() {
    clearTimeout(endTimer);
    if (speaking && !paused) {
      deadline = performance.now() + remainingMs;
      endTimer = setTimeout(stop, remainingMs);
    }
  }
  const send = (type) => parent.postMessage({type}, origin);
  function setAudio(wav) {
    const bytes = new Uint8Array(wav);
    const pointer = Module._malloc(bytes.length);
    try { Module.HEAPU8.set(bytes, pointer); Module._setAudioBuffer(pointer, bytes.length); }
    finally { Module._free(pointer); }
  }
  function stop() {
    speaking = false;
    remainingMs = 0;
    clearTimeout(endTimer);
    isPaused = true;
    cancelAnimationFrame(window.socratiaFrameHandle);
    videoProcessor.pause();
    const video = videoProcessor.video;
    const motion = window.socratiaListeningMotion;
    if (motion?.isAvailable()) {
      motion.seekTo(video.currentTime);
      document.body.dataset.speaking = 'false';
      motion.setActive(!paused);
      return;
    }
    const neutral = () => {
      if (speaking) return;
      if (video.readyState < 2) { video.addEventListener('loadeddata', neutral, {once:true}); return; }
      ctx_video.clearRect(0, 0, canvas_video.width, canvas_video.height);
      ctx_video.drawImage(processChromaKey(video), 0, 0);
    };
    // The upstream clips start with an encoded black lead-in frame.
    const restTime = Math.min(CONFIG.videoSrc.startsWith('assets2/') ? 1.2 : .5, Math.max(0, video.duration - .04));
    if (Math.abs(video.currentTime - restTime) < .01) neutral();
    else { video.addEventListener('seeked', neutral, {once:true}); video.currentTime = restTime; }
    document.body.dataset.speaking = 'false';
    window.socratiaListeningMotion?.setActive(!paused);
  }
  function resume() {
    if (speaking && !paused && isPaused) {
      window.socratiaListeningMotion?.setActive(false);
      isPaused = false; videoProcessor.play(); processVideoFrames();
    }
  }
  window.addEventListener('message', (event) => {
    if (event.source !== parent || event.origin !== origin || !ready) return;
    const message = event.data;
    if (message?.type === 'socratia.listen') document.body.dataset.listening = String(Boolean(message.listening));
    if (message?.type === 'socratia.stop') stop();
    if (message?.type === 'socratia.audio' && message.wav instanceof ArrayBuffer && message.wav.byteLength >= 46) {
      clearTimeout(endTimer);
      setAudio(message.wav);
      const header = new DataView(message.wav);
      let bytesPerSecond = 0, audioBytes = 0;
      for (let at = 12; at + 8 <= header.byteLength;) {
        const tag = String.fromCharCode(...new Uint8Array(message.wav, at, 4));
        const size = header.getUint32(at + 4,true);
        if (tag === 'fmt ' && size >= 16 && at + 24 <= header.byteLength) bytesPerSecond = header.getUint32(at + 16,true);
        if (tag === 'data') { audioBytes = Math.min(size, header.byteLength - at - 8); break; }
        at += 8 + size + (size % 2);
      }
      const duration = audioBytes / bytesPerSecond;
      if (!Number.isFinite(duration) || duration <= .01) { stop(); return; }
      if (!speaking && window.socratiaListeningMotion?.isAvailable()) {
        const time = window.socratiaListeningMotion.getTime();
        if (videoProcessor.video.duration > 0) videoProcessor.video.currentTime = time % videoProcessor.video.duration;
      }
      speaking = true;
      window.socratiaListeningMotion?.setActive(false);
      document.body.dataset.speaking = 'true';
      resume();
      remainingMs = duration * 1000;
      armEnd();
    }
    if (message?.type === 'socratia.pause') {
      if (speaking && !paused && message.paused) {
        remainingMs = Math.max(0, deadline - performance.now());
        clearTimeout(endTimer);
      }
      const wasPaused = paused;
      paused = Boolean(message.paused);
      document.body.dataset.paused = String(paused);
      window.socratiaListeningMotion?.setActive(!paused && !speaking);
      if (paused) { isPaused = true; cancelAnimationFrame(window.socratiaFrameHandle); videoProcessor.pause(); }
      else { resume(); if (wasPaused) armEnd(); }
    }
  });
  async function start() {
    try {
      const avatar = ['assets','assets2','daniel-fictional'][Number(new URLSearchParams(location.search).get('index'))] || 'assets';
      CONFIG.videoSrc = `${avatar}/01.mp4?v=20261018-3`;
      CONFIG.dataSrc = `${avatar}/combined_data.json.gz?v=20261018-3`;
      CONFIG.chromaKeyEnabled = true;
      CONFIG.socratiaVariant = false;
      // Use the room's own backdrop; no external background video is needed.
      setupBackgroundVideo = () => {};
      await createQtAppInstance({locateFile: (name) => name.endsWith('.wasm') ? 'DHLiveMini.wasm' : name});
      await newVideoTask();
      await videoProcessor.video.play();
      ready = true;
      document.body.dataset.paused = 'false';
      document.body.dataset.listening = 'true';
      window.socratiaListeningMotion?.load(avatar);
      stop();
      send('socratia.ready');
    } catch { send('socratia.error'); }
  }
  void start();
})();


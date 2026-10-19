(() => {
  const frames = [...document.querySelectorAll('iframe')];
  const ready = new Set();
  const motionReady = new Set();
  let player, paused = false, previousStatus = '';
  let generation = 0;
  const voices = ['alex-es.wav', 'elena-es.wav', 'daniel-es.wav'];
  const status = document.getElementById('status');
  const post = (frame, message) => frame.contentWindow.postMessage(message, location.origin);
  const stopAll = () => {
    generation++;
    player?.pause(); player = null;
    frames.forEach(frame => post(frame, {type:'socratia.stop'}));
    document.querySelectorAll('article').forEach(article => article.removeAttribute('data-speaking'));
  };
  window.addEventListener('message', event => {
    if (event.origin !== location.origin) return;
    const index = frames.findIndex(frame => frame.contentWindow === event.source);
    if (index < 0) return;
    if (event.data?.type === 'socratia.ready') {
      ready.add(index); status.textContent = `${ready.size}/3 jurados preparados · movimiento facial ${motionReady.size}/3`;
    }
    if (event.data?.type === 'socratia.motion-ready') {
      motionReady.add(index); status.textContent = `${ready.size}/3 jurados preparados · movimiento facial ${motionReady.size}/3`;
    }
    if (event.data?.type === 'socratia.error') status.textContent = `Error al preparar jurado ${index + 1}`;
  });
  document.querySelectorAll('[data-index]').forEach(button => button.addEventListener('click', async () => {
    const index = Number(button.dataset.index);
    if (!ready.has(index)) return;
    stopAll();
    const current = generation;
    try {
      const engine = document.getElementById('engine').value;
      const file = (engine === 'kokoro' ? `neural/kokoro-${['alex','elena','daniel'][index]}.wav` : engine === 'piper' ? 'neural/piper-es.wav' : voices[index]) + '?v=20261018-3';
      const response = await fetch(`common/${file}`);
      if (!response.ok) throw new Error('audio');
      const wav = await window.socratiaLipAudio(await response.arrayBuffer());
      if (current !== generation) return;
      paused = false;
      document.getElementById('pause').textContent = 'Pausar movimientos';
      frames.forEach(frame => post(frame, {type:'socratia.pause',paused:false}));
      player = new Audio(`common/${file}`);
      await player.play();
      if (current !== generation) return;
      post(frames[index], {type:'socratia.audio', wav});
      frames[index].parentElement.dataset.speaking = 'true';
      status.textContent = `${['Alex','Elena','Daniel'][index]} hablando (${engine}) · los otros dos escuchan`;
      player.onended = () => { if (current === generation) { stopAll(); status.textContent = 'Turno finalizado · tribunal en reposo'; } };
      player.onerror = () => { if (current === generation) { stopAll(); status.textContent = 'No se pudo reproducir la voz'; } };
    } catch { if (current === generation) { stopAll(); status.textContent = 'No se pudo preparar la voz'; } }
  }));
  document.getElementById('pause').addEventListener('click', event => {
    paused = !paused;
    if (paused) {
      previousStatus = status.textContent;
      player?.pause();
      status.textContent = 'En pausa · voz y movimientos detenidos';
    } else {
      status.textContent = previousStatus;
      if (player) void player.play().catch(() => { stopAll(); status.textContent = 'No se pudo reanudar la voz'; });
    }
    frames.forEach(frame => post(frame,{type:'socratia.pause',paused}));
    event.target.textContent = paused ? 'Reanudar movimientos' : 'Pausar movimientos';
  });
  document.getElementById('stop').addEventListener('click', () => {
    stopAll();
    paused = false; document.getElementById('pause').textContent = 'Pausar movimientos';
    frames.forEach(frame => post(frame, {type:'socratia.pause',paused:false}));
    status.textContent = 'Voz detenida';
  });
  document.getElementById('engine').addEventListener('change', () => {stopAll();status.textContent='Voces cambiadas · elige un jurado';});
})();

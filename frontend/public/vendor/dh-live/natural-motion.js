// Independent, bounded secondary motion. Never changes lip animation or audio.
// This adds posture shifts to the rendered portrait; it is not body generation.
(() => {
  const canvas = document.getElementById('canvas_video');
  const index = Number(new URLSearchParams(location.search).get('index')) || 0;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let handle = 0, last = 0, elapsed = index * 3.17;
  let x = 0, y = 0, tilt = 0, targetX = 0, targetY = 0, targetTilt = 0;
  let nextShift = 1.8 + index * 1.7, nodAt = 7 + index * 3.6, nodStart = -100;
  let stopped = true;
  function frame(now) {
    const dt = last ? Math.min(.05, (now-last)/1000) : 0;
    last = now; elapsed += dt;
    const speaking = document.body.dataset.speaking === 'true';
    const listening = document.body.dataset.listening === 'true';
    if (elapsed > nextShift) {
      // Irregular holds and small shifts, rather than a synchronized loop.
      targetX = (Math.random()-.5) * 1.8;
      targetY = (Math.random()-.5) * 1.2;
      targetTilt = (Math.random()-.5) * (speaking ? .65 : .4);
      nextShift = elapsed + 3.5 + Math.random()*6;
    }
    if (elapsed > nodAt) {
      if (listening || speaking) nodStart = elapsed;
      nodAt = elapsed + 8 + Math.random()*13;
    }
    const ease = 1-Math.exp(-dt*1.3);
    x += (targetX-x)*ease; y += (targetY-y)*ease; tilt += (targetTilt-tilt)*ease;
    const phase = elapsed-nodStart;
    const nod = phase >= 0 && phase < 1.8 ? Math.sin(phase/1.8*Math.PI)**2 : 0;
    const breath = Math.sin(elapsed*(.83+index*.057))*.32 + Math.sin(elapsed*.39)*.12;
    canvas.style.transformOrigin = '50% 78%';
    canvas.style.transform = `translate3d(${x.toFixed(3)}px,${(y+breath+nod*.9).toFixed(3)}px,0) rotate(${(tilt+nod*.14).toFixed(3)}deg) scale(${(1.012+breath*.0008).toFixed(5)})`;
    handle = requestAnimationFrame(frame);
  }
  function sync() {
    const shouldStop = document.hidden || reduced.matches || document.body.dataset.paused === 'true';
    if (shouldStop === stopped) return;
    stopped = shouldStop;
    cancelAnimationFrame(handle); last = 0;
    if (stopped) canvas.style.transform = '';
    else handle = requestAnimationFrame(frame);
  }
  const observer = new MutationObserver(sync);
  observer.observe(document.body,{attributes:true,attributeFilter:['data-paused']});
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',sync);
  window.addEventListener('pagehide',()=>{cancelAnimationFrame(handle);observer.disconnect();});
  sync();
})();

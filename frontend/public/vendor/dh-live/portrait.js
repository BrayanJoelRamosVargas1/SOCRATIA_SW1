// Native alpha video: no canvas readbacks, inference or rendering timers on supported browsers.
(() => {
  const index=Number(new URLSearchParams(location.search).get('index'))||0;
  const folder=['assets','assets2','daniel-fictional'][index]||'assets';
  const video=document.querySelector('video'),canvas=document.querySelector('canvas');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let native=Boolean(video.canPlayType?.('video/webm; codecs="vp9"'));
  let paused=false,timer,context;
  const send=type=>parent.postMessage({type,renderer:'portrait'},location.origin);
  video.poster=`${folder}/portrait.webp?v=20261019-3`;
  function load(){
    video.hidden=!native;canvas.hidden=native;
    video.src=`${folder}/${native?'listening-lite.webm':'listening.mp4'}?v=${native?'20261019-3':'20261018-3'}`;
  }
  function draw(){
    clearTimeout(timer);
    if(native || document.hidden || paused)return;
    if(video.readyState>=2){
      context??=canvas.getContext('2d',{willReadFrequently:true});
      context.drawImage(video,0,0,canvas.width,canvas.height);
      const frame=context.getImageData(0,0,canvas.width,canvas.height),pixels=frame.data;
      for(let at=0;at<pixels.length;at+=4){const r=pixels[at],g=pixels[at+1],b=pixels[at+2];if(g>65 && g>r*1.3 && g>b*1.2)pixels[at+3]=0;}
      context.putImageData(frame,0,0);
    }
    if(!reduced.matches)timer=setTimeout(draw,100);
  }
  function sync(){
    clearTimeout(timer);
    if(document.hidden || paused || reduced.matches){video.pause();if(!native && !document.hidden && !paused)draw();}
    else void video.play().then(()=>{if(!native)draw();}).catch(()=>{if(!native)draw();});
  }
  video.addEventListener('loadeddata',()=>{
    if(Number.isFinite(video.duration))video.currentTime=(.5+index*1.37)%video.duration;
    sync();send('socratia.ready');
  });
  video.addEventListener('seeked',()=>{if(!native && reduced.matches)draw();});
  video.addEventListener('error',()=>{if(native){native=false;load();}else send('socratia.error');});
  window.addEventListener('message',event=>{
    if(event.origin!==location.origin || event.source!==parent)return;
    if(event.data?.type==='socratia.pause'){paused=Boolean(event.data.paused);sync();}
  });
  document.addEventListener('visibilitychange',sync);reduced.addEventListener('change',sync);
  window.addEventListener('pagehide',()=>{clearTimeout(timer);video.pause();});
  load();
})();

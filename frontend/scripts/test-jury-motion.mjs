import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../public/vendor/dh-live/natural-motion.js',import.meta.url),'utf8');
function actor(index) {
  const style={},dataset={paused:'false',speaking:'false',listening:'true'};
  let callback,observer,handle=0;
  const context={
    document:{hidden:false,body:{dataset},getElementById:()=>({style}),addEventListener(){}},
    location:{search:`?index=${index}`},URLSearchParams,
    matchMedia:()=>({matches:false,addEventListener(){}}),
    requestAnimationFrame(fn){callback=fn;return ++handle;},cancelAnimationFrame(){callback=null;},
    MutationObserver:class{constructor(fn){observer=fn;}observe(){}disconnect(){}},
    window:{addEventListener(){}},
  };
  vm.runInNewContext(source,context);
  return {style,dataset,tick(now){callback?.(now);},pause(){dataset.paused='true';observer();},resume(){dataset.paused='false';observer();},running:()=>Boolean(callback)};
}
const actors=[0,1,2].map(actor);
for(let time=0;time<1200;time+=40)actors.forEach(actor=>actor.tick(time));
assert.equal(new Set(actors.map(actor=>actor.style.transform)).size,3,'listeners must have independent phases');
actors.forEach(actor=>{assert.equal(actor.dataset.speaking,'false');actor.pause();assert.equal(actor.running(),false);assert.equal(actor.style.transform,'');actor.resume();assert.equal(actor.running(),true);});
console.log('PASS: three independent listeners, no speech changes, pause and resume.');

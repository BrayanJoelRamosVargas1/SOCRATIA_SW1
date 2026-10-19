// Only the active human renderer is allocated; waiters never hold up speech forever.
const ready=new Set<number>();
const pending=new Map<number,Set<(value:boolean)=>void>>();
export function setJuryRendererReady(index:number,value:boolean){
 if(value)ready.add(index);else ready.delete(index);
 if(value){pending.get(index)?.forEach(resolve=>resolve(true));pending.delete(index);}
}
export function waitForJuryRenderer(index:number,timeout=6000):Promise<boolean>{
 if(ready.has(index))return Promise.resolve(true);
 return new Promise(resolve=>{
  const done=(value:boolean)=>{clearTimeout(timer);pending.get(index)?.delete(done);resolve(value);};
  const list=pending.get(index)??new Set();list.add(done);pending.set(index,list);
  const timer=setTimeout(()=>done(false),timeout);
 });
}

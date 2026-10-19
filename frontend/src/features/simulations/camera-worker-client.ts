import type { FaceLandmarkerResult, PoseLandmarkerResult } from "@mediapipe/tasks-vision";

type Capabilities = {pose:boolean;face:boolean};
export type CameraFrameResult = {pose:PoseLandmarkerResult|null;face:FaceLandmarkerResult|null;elapsed:number};

export function createCameraWorker() {
  const worker = new Worker("/vision/camera-worker.js?v=20261019-1");
  let pending: {resolve:(result:CameraFrameResult)=>void;reject:(error:Error)=>void;timer:ReturnType<typeof setTimeout>}|undefined;
  let sequence = 0, closed = false, capturing = false;
  let resolveReady:(value:Capabilities)=>void, rejectReady:(error:Error)=>void;
  const ready = new Promise<Capabilities>((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
  const startup = setTimeout(()=>fail(new Error("El detector tardó demasiado en iniciar.")),60000);
  function fail(error:Error) {
    clearTimeout(startup);
    rejectReady(error);
    if (pending) {clearTimeout(pending.timer);pending.reject(error);pending=undefined;}
  }
  worker.onerror=()=>fail(new Error("No pudimos iniciar el detector independiente de cámara."));
  worker.onmessage=({data})=>{
    if(data.type==="ready"){clearTimeout(startup);resolveReady({pose:data.pose,face:data.face});}
    else if(data.type==="error")fail(new Error("No se pudo cargar ningún detector."));
    else if(pending && data.id===sequence){
      const current=pending;pending=undefined;clearTimeout(current.timer);
      if(data.type==="result")current.resolve(data);
      else current.reject(new Error("No pudimos analizar este fotograma."));
    }
  };
  worker.postMessage({type:"init"});
  return {
    ready,
    async detect(video:HTMLVideoElement,timestamp:number):Promise<CameraFrameResult>{
      if(closed || pending || capturing)throw new Error("Detector no disponible.");
      capturing=true;
      let bitmap:ImageBitmap;
      try {bitmap=await createImageBitmap(video);}
      finally {capturing=false;}
      if(closed){bitmap.close();throw new Error("Detector detenido.");}
      return new Promise((resolve,reject)=>{
        const id=++sequence;
        pending={resolve,reject,timer:setTimeout(()=>{pending=undefined;reject(new Error("El detector dejó de responder."));},8000)};
        try {worker.postMessage({type:"frame",id,bitmap,timestamp},[bitmap]);}
        catch {bitmap.close();clearTimeout(pending.timer);pending=undefined;reject(new Error("No se pudo enviar el fotograma."));}
      });
    },
    close(){closed=true;fail(new Error("Detector detenido."));worker.terminate();},
  };
}

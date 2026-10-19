import type {FaceSignals,VisualSignals} from "./practice-signals";
import type {CameraQuality} from "./camera-quality";
import type {AppearanceStatus} from "./appearance-feedback";
export type Observation = {id:string;text:string;holdMs:number};
export type CoachInput = {presence:"present"|"absent"|"unknown";face:FaceSignals;pose:VisualSignals;torsoTilt:number|null;status:"off"|"starting"|"ready"|"error";appearance:AppearanceStatus;quality:CameraQuality};
export function getObservations({presence,face,pose,torsoTilt,status,appearance,quality}:CoachInput):Observation[]{
  const result:Observation[]=[];
  const add=(id:string,text:string,holdMs=1500)=>result.push({id,text,holdMs});
  if(status!=="ready")return result;
  if(quality.freshness==="stale"){add("stale","La cámara dejó de enviar imágenes nuevas. Reiníciala o selecciona otra cámara.",0);return result;}
  if(quality.freshness!=="live")return result;
  if(quality.lighting==="dim")add("dim","La imagen está oscura. Añade una luz delante de ti para poder revisar rostro y postura.");
  if(quality.lighting==="bright")add("bright","La imagen está sobreexpuesta. Reduce la luz directa para que se distingan tus rasgos.");
  if(quality.lighting==="backlit")add("backlit","La luz detrás de ti deja tu rostro oscuro. Coloca la luz delante de la cámara.");
  if((quality.faces??0)>1){add("multiple","Se detectan varios rostros. Quédate solo en el encuadre para medir tu mirada y postura.",1000);return result;}
  if(presence==="absent"){add("absent","No se detecta una persona. Vuelve a colocarte frente a la cámara.",800);return result;}
  if(presence!=="present")return result;
  if(!face.detected)add("no-face","Se detecta parte del cuerpo, pero no el rostro. Muestra la cara para poder revisar la mirada.");
  if(face.direction==="away")add("gaze",face.reason==="head_turned" ? "Estás girando la cabeza fuera de la cámara. Mira hacia la lente al dirigirte al tribunal." : "Estás mirando fuera de la cámara. Levanta la mirada hacia la lente.");
  if(face.eyes==="closed")add("eyes","Se detectan los ojos cerrados. Abre los ojos para comprobar la mirada.",2200);
  else if(face.detected && face.reason==="no_iris")add("iris","No se pueden verificar tus iris. Acerca el rostro y mejora la luz; la mirada no se está dando por correcta.",2500);
  if((torsoTilt??0)>12 || (pose.shoulderTilt??0)>10)add("posture","Tu postura está inclinada. Centra el torso y nivela los hombros.",2200);
  if(pose.reliable && pose.centered===false)add("center","Estás fuera del centro del encuadre. Colócate frente a la cámara.");
  if(face.framing==="cropped")add("crop","Tu rostro está cortado por el borde. Ajusta la cámara para mostrar la cabeza completa.");
  else if(face.framing==="near" || pose.framing==="near")add("distance","Estás demasiado cerca de la cámara. Aléjate un poco para mostrar rostro y hombros.");
  else if(face.framing==="far" || pose.framing==="far")add("distance","Estás lejos de la cámara. Acércate para que se distingan los ojos y la expresión.");
  if((face.headTilt??0)>15)add("head","Tu cabeza está inclinada hacia un hombro. Prueba una posición más nivelada.",2200);
  if((pose.handsNearFace??0)>0)add("hands","Hay una mano cerca del rostro. Procura dejar la cara despejada al explicar tus ideas.",2500);
  if(appearance.state==="result"){
    const clothing=appearance.result;
    if(clothing?.presentation==="incomplete")add("clothing","No se observa una prenda en el torso. Ponte una camisa o blusa para practicar la defensa.",0);
    else if(clothing?.presentation==="casual")add("clothing","Tu vestimenta es casual. Para ensayar una presentación formal, usa una camisa, blusa o saco.",0);
    else if(clothing?.presentation==="uncertain")add("clothing",clothing.upper_body_visible ? "La ropa no se pudo verificar con este encuadre. Mejora la luz y muestra claramente las prendas." : "No se ve suficiente torso para comprobar la ropa. Aleja o baja un poco la cámara.",0);
  }
  if(appearance.state==="error")add("clothing-error","La revisión de vestimenta falló. Consulta el aviso y vuelve a intentarlo.",0);
  return result;
}

// Only continuous observations become warnings. A blink or an isolated noisy
// frame must not produce a spoken correction. Resolved conditions clear at once.
export class ObservationTracker {
  private started=new Map<string,{at:number;text:string}>();
  update(observations:Observation[],now:number):Observation[]{
    const ids=new Set(observations.map(item=>item.id));
    for(const id of this.started.keys())if(!ids.has(id))this.started.delete(id);
    return observations.filter(item=>{
      let entry=this.started.get(item.id);
      if(!entry || entry.text!==item.text){entry={at:now,text:item.text};this.started.set(item.id,entry);}
      return now-entry.at>=item.holdMs;
    });
  }
}

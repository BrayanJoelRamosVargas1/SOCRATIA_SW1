"use client";
import {useEffect,useState} from "react";
import {apiRequest} from "@/lib/api";
function bytes(value:string){const raw=atob(value.replace(/-/g,"+").replace(/_/g,"/")+"=".repeat((4-value.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0));}
function payload(sub:PushSubscription){const item=sub.toJSON();return {endpoint:sub.endpoint,p256dh:item.keys?.p256dh,auth:item.keys?.auth};}
export function PreparationNotifications(){
 const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 const [config,setConfig]=useState<{enabled:boolean;public_key:string}|null>(null);
 useEffect(()=>{let active=true;void apiRequest<{enabled:boolean;public_key:string}>("/push/config").then(value=>{if(active)setConfig(value);}).catch(()=>{if(active)setMessage("No se pudo consultar el servicio de avisos.");});return()=>{active=false;};},[]);
 async function enable(){
  setBusy(true);
  try{
   if(!("serviceWorker" in navigator)||!("PushManager" in window)||!("Notification" in window)){setMessage("Tu navegador no admite push. En iPhone, instala Socratia desde Safari: Compartir â†’ AÃ±adir a inicio.");return;}
   if(!config?.enabled){setMessage("Las notificaciones aÃºn no estÃ¡n disponibles en este servidor.");return;}
   const permission=await Notification.requestPermission();
   if(permission!=="granted"){setMessage("No activaste los avisos. Puedes cambiar el permiso en tu navegador.");return;}
   const registration=await navigator.serviceWorker.register("/sw.js");await navigator.serviceWorker.ready;
   const sub=await registration.pushManager.getSubscription() || await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes(config.public_key)});
   await apiRequest("/push/subscriptions",{method:"POST",body:JSON.stringify(payload(sub))});
   setMessage("Avisos activados para esta cuenta en este dispositivo. Te avisaremos al terminar la preparaciÃ³n.");
  }catch{setMessage("No se pudo activar. Revisa el permiso y tu conexiÃ³n.");}finally{setBusy(false);}
 }
 async function disable(){
  setBusy(true);try{
   const registration=await navigator.serviceWorker.getRegistration();const sub=await registration?.pushManager.getSubscription();
   if(sub){await apiRequest("/push/subscriptions",{method:"DELETE",body:JSON.stringify(payload(sub))});await sub.unsubscribe();}
   setMessage("Avisos desactivados en este dispositivo.");
  }catch{setMessage("No se pudo desactivar. IntÃ©ntalo de nuevo.");}finally{setBusy(false);}
 }
 return <aside style={{margin:"16px 0",padding:16,border:"1px solid #cbdcd6",borderRadius:12}}><strong>Avisos de preparaciÃ³n</strong><p>Recibe una notificaciÃ³n cuando tu material estÃ© listo, incluso si sales de esta pÃ¡gina. No mostramos el contenido de tu documento.</p><button type="button" className="button" disabled={busy||!config?.enabled} onClick={()=>void enable()}>Activar avisos</button> <button type="button" className="button" disabled={busy} onClick={()=>void disable()}>Desactivar</button><p role="status">{message || (config&&!config.enabled?"Los avisos aún no están configurados en este servidor.":"")}</p></aside>;
}

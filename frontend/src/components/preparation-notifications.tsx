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
   if(!("serviceWorker" in navigator)||!("PushManager" in window)||!("Notification" in window)){setMessage("Tu navegador no admite push. En iPhone, instala Socratia desde Safari: Compartir → Añadir a inicio.");return;}
   if(!config?.enabled){setMessage("Las notificaciones aún no están disponibles en este servidor.");return;}
   const permission=await Notification.requestPermission();
   if(permission!=="granted"){setMessage("No activaste los avisos. Puedes cambiar el permiso en tu navegador.");return;}
   const registration=await navigator.serviceWorker.register("/sw.js");await navigator.serviceWorker.ready;
   const sub=await registration.pushManager.getSubscription() || await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes(config.public_key)});
   await apiRequest("/push/subscriptions",{method:"POST",body:JSON.stringify(payload(sub))});
   setMessage("Avisos activados para esta cuenta en este dispositivo. Te avisaremos al terminar la preparación.");
  }catch{setMessage("No se pudo activar. Revisa el permiso y tu conexión.");}finally{setBusy(false);}
 }
 async function test(){
  setBusy(true);
  try{
   const result=await apiRequest<{accepted:number;failed:number}>("/push/test",{method:"POST"});
   setMessage(result.accepted>0 ? "El servicio aceptó el aviso. Comprueba que aparezca en tu dispositivo; la aceptación no confirma su recepción." : result.failed>0 ? "No se pudo entregar el aviso. Desactiva y activa los avisos para renovar la suscripción." : "Primero activa los avisos en este dispositivo.");
  }catch{setMessage("No se pudo probar el aviso. Espera un minuto, revisa los permisos y vuelve a intentar.");}finally{setBusy(false);}
 }
 async function disable(){
  setBusy(true);try{
   const registration=await navigator.serviceWorker.getRegistration();const sub=await registration?.pushManager.getSubscription();
   if(sub){await apiRequest("/push/subscriptions",{method:"DELETE",body:JSON.stringify(payload(sub))});await sub.unsubscribe();}
   setMessage("Avisos desactivados en este dispositivo.");
  }catch{setMessage("No se pudo desactivar. Inténtalo de nuevo.");}finally{setBusy(false);}
 }
 return <aside style={{margin:"16px 0",padding:16,border:"1px solid #cbdcd6",borderRadius:12}}><strong>Avisos de preparación</strong><p>Recibe una notificación cuando tu material esté listo, incluso si sales de esta página. No mostramos el contenido de tu documento.</p><p>Android: abre Socratia en un navegador compatible, como Chrome. iPhone o iPad: requiere iOS/iPadOS 16.4 o posterior; desde Safari usa Compartir → Añadir a pantalla de inicio y abre Socratia desde su icono. Después pulsa Activar avisos y acepta el permiso.</p><button type="button" className="button" disabled={busy||!config?.enabled} onClick={()=>void enable()}>Activar avisos</button> <button type="button" className="button" disabled={busy} onClick={()=>void disable()}>Desactivar</button> <button type="button" className="button" disabled={busy||!config?.enabled} onClick={()=>void test()}>Probar aviso</button><p role="status">{message || (config&&!config.enabled?"Los avisos aún no están configurados en este servidor.":"")}</p></aside>;
}

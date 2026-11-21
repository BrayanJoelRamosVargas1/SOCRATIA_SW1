import { Capacitor } from '@capacitor/core';
import { api, ApiError, exportFile, clearPrivateExports } from './api';
import { enablePush, disablePush, initializePush, getPushState, restorePush } from './push';
import './style.css';
import { mountHelp, openWebProcedure } from './help';

type Document = {id:string; original_name:string; status:string; file_size:number};
type Simulation = {id:string; status:string; document:{name:string}; created_at:string};
const root = document.querySelector<HTMLDivElement>('#app')!;
let user: {full_name:string} | null = null;
let generation = 0;
let busy = false;
let pendingNotification: string | null | undefined;
const labels: Record<string,string> = {UPLOADED:'Recibido',PROCESSING:'Procesando',PROCESSED:'Procesado',FAILED:'Requiere revisión',READY:'Listo',DRAFT:'Preparada',ACTIVE:'En curso',ABORTED:'Interrumpida',ERROR:'Requiere revisión',COMPLETED:'Finalizada',FINISHED:'Finalizada',EVALUATED:'Evaluada',CREATED:'Preparada',IN_PROGRESS:'En curso',CANCELLED:'Cancelada',METHODOLOGICAL:'Metodología',TECHNICAL:'Técnica',CRITICAL:'Análisis crítico',GENERAL:'General'};
function el<K extends keyof HTMLElementTagNameMap>(tag:K, text='', className='') {const node=document.createElement(tag); node.textContent=text; node.className=className; return node;}
function button(text:string, action:()=>unknown, secondary=false) {const node=el('button',text,secondary?'secondary':''); node.type='button'; node.addEventListener('click',()=>{void perform(action);}); return node;}
function announce(message:string, success=false) {const box=document.querySelector('#message'); if (box) {box.textContent=message; box.classList.toggle('message-success',success);box.scrollIntoView({block:'nearest'});}}
async function perform(action:()=>unknown) {
  if(busy) return;
  busy=true;
  try {await action();} catch(error) {if(error instanceof ApiError && error.status===401){user=null;login();}announce(error instanceof Error?error.message:'No se pudo completar la acción.');}
  finally {busy=false;if(user && pendingNotification!==undefined)void perform(()=>openPreparation());}
}
function frame(title:string) {
  const ticket=++generation;
  root.replaceChildren();
  const header=el('header'); header.append(el('span','S','brand'),el('div','Socratia'));
  const main=el('main'); main.append(el('p',user?.full_name ?? 'Tu preparación, contigo','eyebrow'),el('h1',title));
  const message=el('p','','message'); message.id='message'; message.setAttribute('role','status'); main.append(message);
  root.append(header,main);
  if(user){const nav=el('nav');nav.setAttribute('aria-label','Secciones');for(const [label,action,active] of [
    ['Documentos',()=>show('documents'),title==='Mis documentos'],
    ['Resultados',()=>show('results'),title==='Mis resultados'],
    ['Mi cuenta',()=>settings(),title==='Mi cuenta'],
    ['Ayuda',()=>help(),title==='Ayuda'],
  ] as const){const item=button(label,action,true);if(active)item.setAttribute('aria-current','page');nav.append(item);}root.append(nav);}
  return {main,ticket};
}
function login() {
  const {main}=frame('Continúa tu preparación');
  main.append(el('p','Entra con tu cuenta de Socratia para consultar tus materiales y resultados.'));
  const form=el('form');
  const emailLabel=el('label','Correo electrónico'), email=el('input');email.type='email';email.autocomplete='username';email.required=true;emailLabel.append(email);
  const passwordLabel=el('label','Contraseña'), password=el('input');password.type='password';password.autocomplete='current-password';password.required=true;passwordLabel.append(password);
  const submit=el('button','Iniciar sesión');submit.type='submit';form.append(emailLabel,passwordLabel,submit);
  form.addEventListener('submit',event=>{event.preventDefault();void perform(async()=>{submit.disabled=true;try {const response=await api<{user:{full_name:string}}>('/auth/login','POST',{email:email.value.trim(),password:password.value});password.value='';user=response.user;await openPreparation();}finally{submit.disabled=false;}});});
  main.append(form,button('¿Olvidaste tu contraseña?',()=>openWebProcedure('/forgot-password'),true),el('p','La creación de cuentas y las simulaciones se realizan en la versión web.','hint'));
}
function help(){
  const {main}=frame('Ayuda');
  mountHelp(main,section=>{void perform(()=>section==='account'?settings():show(section==='results'?'results':'documents'));});
}
async function show(page:'documents'|'results') {
  const {main,ticket}=frame(page==='documents'?'Mis documentos':'Mis resultados');
  const placeholder=el('div','','skeleton');placeholder.setAttribute('aria-label','Consultando tus materiales');main.append(placeholder);
  try {
    if(page==='documents') {
      const rows=await api<Document[]>('/documents');if(ticket!==generation)return;placeholder.remove();
      if(!rows.length)main.append(el('p','Aún no tienes documentos. Sube tu material desde Socratia en la web.','card'));
      for(const row of rows){const card=el('article','','card');card.append(el('h2',row.original_name),el('p',`${labels[row.status]??'En preparación'} · ${(row.file_size/1024/1024).toFixed(1)} MB`),button('Ver materiales',()=>documentDetail(row.id,row.original_name),true));main.append(card);}
    } else {
      const rows=await api<Simulation[]>('/simulations');if(ticket!==generation)return;placeholder.remove();
      if(!rows.length)main.append(el('p','Aquí aparecerán los resultados de tus defensas realizadas en la web.','card'));
      for(const row of rows){const card=el('article','','card');card.append(el('h2',row.document.name),el('p',`${labels[row.status]??'En preparación'} · ${new Date(row.created_at).toLocaleDateString('es-BO')}`),button('Ver evaluación',()=>evaluation(row.id),true));main.append(card);}
    }
    main.append(button('Actualizar',()=>show(page),true));
  } catch(error){if(ticket===generation)placeholder.remove();throw error;}
}
async function documentDetail(id:string,title:string) {
  const {main,ticket}=frame(title);
  const results=await Promise.allSettled([
    api<{questions:{question:string;category:string}[]}>(`/documents/${id}/questions`),
    api<{title:string;slides:{title:string;bullet_points:string[];speaker_notes:string}[]}>(`/documents/${id}/presentation`),
  ]);
  if(ticket!==generation)return;
  const [questions,slides]=results;
  for(const [kind,result] of [['Preguntas',questions],['Diapositivas',slides]] as const){if(result.status==='rejected'){if(result.reason instanceof ApiError && result.reason.status===401)throw result.reason;main.append(el('p',`${kind}: ${result.reason instanceof ApiError && result.reason.status===404?'todavía no disponibles. Prepáralas desde la web.':'no se pudieron consultar. Puedes volver a intentar.'}`,'card'));}}
  if(questions.status==='fulfilled'){
    main.append(el('h2','Banco de preguntas'),button('Guardar o compartir PDF',()=>exportFile(id,'questions')));
    questions.value.questions.forEach((question,index)=>{const card=el('article','','card');card.append(el('p',labels[question.category]??'Pregunta','eyebrow'),el('h3',`${index+1}. ${question.question}`));main.append(card);});
  }
  if(slides.status==='fulfilled'){
    main.append(el('h2',slides.value.title),button('Guardar o compartir PowerPoint',()=>exportFile(id,'presentation')));
    for(const slide of slides.value.slides){const card=el('details','','card');card.append(el('summary',slide.title));const list=el('ul');for(const point of slide.bullet_points)list.append(el('li',point));card.append(list,el('p',slide.speaker_notes));main.append(card);}
  }
  main.append(button('Volver a documentos',()=>show('documents'),true));
}
async function evaluation(id:string) {
  const {main,ticket}=frame('Evaluación de mi defensa');
  const result=await api<{overall_score:number|null;turn_evaluations:{strengths:string[];weaknesses:string[]}[]}>(`/simulations/${id}/evaluation`);
  if(ticket!==generation)return;
  main.append(el('p',result.overall_score===null?'Evaluación en preparación':`${result.overall_score.toFixed(0)} / 100`,'score'));
  for(const [index,turn] of result.turn_evaluations.entries()){const card=el('article','','card');card.append(el('h2',`Respuesta ${index+1}`));for(const text of [...turn.strengths,...turn.weaknesses])card.append(el('p',text));main.append(card);}
  main.append(button('Volver a resultados',()=>show('results'),true));
}
async function settings(notice='') {
  const {main,ticket}=frame('Mi cuenta');
  const card=el('section','','card settings-card');
  const heading=el('div','','settings-heading');heading.append(el('span','↗','settings-symbol'),el('h2','Tus notificaciones'));
  const state=el('p','Comprobando avisos…','push-state');state.setAttribute('aria-live','polite');
  card.append(heading,state,el('p','Te avisamos cuando tus preguntas y diapositivas estén listas, aunque salgas de Socratia.'));
  const controls=el('div','','settings-actions');card.append(controls,el('p','Tus documentos permanecen privados. Los avisos no muestran su contenido.','hint'));main.append(card);
  main.append(el('p','Consulta y repasa tus materiales aquí. Prepara tus defensas desde Socratia en la web.','hint companion-hint'));
  const logout=button('Cerrar sesión',async()=>{
    let pushError=false;
    try {const config=await api<{enabled:boolean}>('/push/native');if(config.enabled)await disablePush();}catch {pushError=true;}
    await api('/auth/logout','POST');
    if(Capacitor.isNativePlatform())await clearPrivateExports();
    pendingNotification=undefined;user=null;login();
    if(pushError)announce('Sesión cerrada. No pudimos desactivar los avisos; puedes revocarlos desde los ajustes de Android.');
  },true);logout.classList.add('logout');main.append(logout);
  if(notice)announce(notice,true);
  try {
    if(!Capacitor.isNativePlatform()){state.textContent='Disponible en tu celular';return;}
    const status=await getPushState();if(ticket!==generation)return;
    state.textContent=status.enabled?'● Notificaciones activadas':status.available?'○ Notificaciones desactivadas':'Avisos no disponibles por el momento';
    state.classList.toggle('push-enabled',status.enabled);
    if(status.available){
      controls.append(button(status.enabled?'Desactivar avisos':'Activar notificaciones',async()=>{
        if(status.enabled)await disablePush();else await enablePush();
        await settings(status.enabled?'Avisos desactivados.':'Ya puedes recibir novedades en este celular.');
      },status.enabled));
      if(status.enabled)controls.append(button('Enviar aviso de prueba',async()=>{
        const result=await api<{accepted:number;failed:number}>('/push/native/test','POST');
        announce(result.accepted?'Aviso enviado. Revisa la barra de notificaciones de tu celular.':result.failed?'No pudimos enviar el aviso. Desactiva y vuelve a activar las notificaciones.':'Activa las notificaciones en este celular antes de probar.',result.accepted>0);
      },true));
    }
  }catch(error){
    if(ticket!==generation)return;
    if(error instanceof ApiError && error.status===401)throw error;
    state.textContent='No pudimos comprobar tus avisos';
    controls.append(button('Volver a comprobar',()=>settings(),true));
  }
}
async function openPreparation(){
  const target=pendingNotification;pendingNotification=undefined;
  if(target)await documentDetail(target,'Mis materiales');else await show('documents');
  if(Capacitor.isNativePlatform())try{await restorePush();}catch{/* Materials remain usable when push is unavailable. */}
}
async function boot(){frame('Mi preparación');try{
  if(Capacitor.isNativePlatform())try{await initializePush(id=>{pendingNotification=id;if(user)void perform(()=>openPreparation());},message=>announce(message,true));}catch{/* Notification setup must not block access to materials. */}
  user=await api<{full_name:string}>('/profile');await openPreparation();
}catch(error){login();if(!(error instanceof ApiError && error.status===401))announce(error instanceof Error?error.message:'No pudimos conectar.');}}
void boot();

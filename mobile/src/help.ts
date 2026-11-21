import { api, SERVER } from './api';
import { helpDestination } from './policy.mjs';

type HelpReply={answer:string;explanation?:string;url:string;engine:string;platform:string};
export async function openWebProcedure(path:string){
 const destination=helpDestination(path);
 if(!destination?.web)throw new Error('Este enlace no está disponible.');
 const {Browser}=await import('@capacitor/browser');
 await Browser.open({url:SERVER+path});
}
export function mountHelp(main:HTMLElement,onNavigate:(section:string)=>void){
 const section=document.createElement('section');section.className='card help-card';section.setAttribute('aria-label','Ayuda de Socratia');
 const heading=document.createElement('h2');heading.textContent='¿Cómo uso Socratia?';
 const intro=document.createElement('p');intro.textContent='Consulta y repasa aquí. Te indicamos cuándo una operación se realiza en la web.';
 const form=document.createElement('form');const label=document.createElement('label');label.textContent='Tu pregunta';
 const input=document.createElement('textarea');input.required=true;input.minLength=2;input.maxLength=600;input.rows=3;input.name='question';label.append(input);
 const aiLabel=document.createElement('label');aiLabel.className='help-choice';const ai=document.createElement('input');ai.type='checkbox';
 aiLabel.append(ai,document.createTextNode(' Explicar con IA (usa cuota)'));
 const submit=document.createElement('button');submit.type='submit';submit.textContent='Consultar';
 const response=document.createElement('div');response.setAttribute('role','status');response.setAttribute('aria-live','polite');response.className='help-response';
 let busy=false;
 async function ask(question:string){
  if(busy)return;busy=true;submit.disabled=true;response.replaceChildren();response.textContent='Buscando orientación…';
  try{
   const reply=await api<HelpReply>('/help/ask','POST',{question,platform:'android',use_ai:ai.checked});
   if(reply.platform!=='android')throw new Error('La ayuda necesita una actualización del servidor. Tus materiales siguen disponibles; por ahora consulta la ayuda desde Socratia en la web.');
   response.replaceChildren();const canonical=document.createElement('p');canonical.textContent=reply.answer;response.append(canonical);
   if(reply.explanation){const title=document.createElement('h3');title.textContent='Explicación con IA';const explanation=document.createElement('p');explanation.textContent=reply.explanation;response.append(title,explanation);}
   const state=document.createElement('p');state.className='hint';state.textContent=reply.engine==='groq'?'Explicación con IA externa':reply.engine==='modelo_propio'?'Explicación de modelo propio':reply.engine==='guia_local_ia_no_disponible'?'La IA no respondió de forma completa. Puedes seguir los pasos verificados.':'Guía del producto sin IA';response.append(state);
   const destination=helpDestination(reply.url);
   if(destination){
    const button=document.createElement('button');button.type='button';button.className='secondary';
    button.textContent=destination.web?'Abrir en la web':'Ir a ese apartado';
    button.addEventListener('click',()=>{
     if(destination.web){void openWebProcedure(reply.url).catch(()=>{state.textContent='Abre Socratia en tu navegador para continuar en la web.';});}
     else onNavigate(destination.section);
    });response.append(button);
   }
  }catch(error){response.textContent=error instanceof Error?error.message:'No pudimos consultar la ayuda. Revisa Internet y vuelve a intentar.';}
  finally{busy=false;submit.disabled=false;}
 }
 const shortcuts=document.createElement('div');shortcuts.className='help-shortcuts';
 for(const question of ['Ver mis materiales','Descargar preguntas en PDF','Recuperar contraseña','Activar notificaciones']){
  const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=question;button.addEventListener('click',()=>{input.value=question;void ask(question);});shortcuts.append(button);
 }
 form.addEventListener('submit',event=>{event.preventDefault();if(input.value.trim().length>=2)void ask(input.value.trim());});
 form.append(label,aiLabel,submit);section.append(heading,intro,shortcuts,form,response);main.append(section);
}

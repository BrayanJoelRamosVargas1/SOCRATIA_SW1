"use client";
import {useState} from "react";
import Link from "next/link";
import {apiRequest} from "@/lib/api";
type Reply={answer:string;explanation?:string;url:string;engine?:string;platform?:string};
const webPaths=new Set(["/documents","/simulations/new","/history","/profile","/forgot-password","/register","/login","/admin/users"]);
export function ProductGuide(){
 const [open,setOpen]=useState(false),[question,setQuestion]=useState(""),[busy,setBusy]=useState(false),[useAI,setUseAI]=useState(false);
 const [reply,setReply]=useState<Reply|null>(null);
 async function ask(text:string){
  if(busy)return;
  setBusy(true);
  try{setReply(await apiRequest<Reply>("/help/ask",{method:"POST",body:JSON.stringify({question:text,use_ai:useAI,platform:"web"})}));}
  catch{setReply({answer:"No pudimos consultar la ayuda. Revisa tu conexión y sesión; puedes volver a intentar.",url:"/login"});}
  finally{setBusy(false);}
 }
 return <div style={{position:"fixed",right:16,bottom:16,zIndex:70,maxWidth:"calc(100vw - 32px)"}}>
 {open&&<section aria-label="Guía de Socratia" style={{background:"white",color:"#14343b",padding:20,borderRadius:16,boxShadow:"0 8px 40px #1235",width:340,maxWidth:"100%",maxHeight:"70vh",overflowY:"auto"}}>
 <h2>¿Cómo uso Socratia?</h2><p>Instrucciones verificadas del producto. Puedes pedir una explicación adicional con IA.</p>
 <div>{["Subir documento","Generar preguntas","Recuperar contraseña","Activar avisos"].map(text=><button className="button" type="button" key={text} disabled={busy} onClick={()=>void ask(text)}>{text}</button>)}</div>
 <label><input type="checkbox" checked={useAI} onChange={e=>setUseAI(e.target.checked)}/> Explicar con IA (usa cuota si no hay modelo propio conectado)</label>
 <form onSubmit={e=>{e.preventDefault();void ask(question);}}><label htmlFor="product-question">¿En qué paso necesitas ayuda?</label>
 <input id="product-question" value={question} maxLength={600} onChange={e=>setQuestion(e.target.value)} style={{width:"100%",padding:10}}/>
 <button className="button" disabled={busy||question.trim().length<2}>{busy?"Buscando orientación…":"Consultar"}</button></form>
 {reply&&<div role="status" style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}><h3>Pasos en Socratia</h3><p>{reply.answer}</p>
 {reply.explanation&&<><h3>Explicación con IA</h3><p>{reply.explanation}</p></>}
 <small>{reply.engine==="guia_local_ia_no_disponible"?"La IA no respondió de forma completa. Puedes seguir los pasos verificados.":reply.engine==="modelo_propio"?"Explicación de modelo propio":reply.engine==="groq"?"Explicación con IA externa":"Guía del producto sin IA"}</small>
 {webPaths.has(reply.url)&&<p><Link href={reply.url}>Ir a ese apartado</Link></p>}</div>}
 </section>}
 <button className="button button-primary" type="button" aria-expanded={open} onClick={()=>setOpen(!open)}>{open?"Cerrar ayuda":"Ayuda con Socratia"}</button></div>;
}

"use client";
import {useState} from "react";
import Link from "next/link";
import {apiRequest} from "@/lib/api";
export function ProductGuide(){
 const [open,setOpen]=useState(false);const [question,setQuestion]=useState("");const [busy,setBusy]=useState(false);
 const [useAI,setUseAI]=useState(false);
 const [reply,setReply]=useState<{answer:string;url:string;engine?:string}|null>(null);
 async function ask(text:string){setBusy(true);try{setReply(await apiRequest("/help/ask",{method:"POST",body:JSON.stringify({question:text,use_ai:useAI})}));}catch{setReply({answer:"Inicia sesiÃ³n para usar la guÃ­a o revisa tu conexiÃ³n.",url:"/login"});}finally{setBusy(false);}}
 return <div style={{position:"fixed",right:16,bottom:16,zIndex:70,maxWidth:"calc(100vw - 32px)"}}>
 {open&&<section aria-label="GuÃ­a de Socratia" style={{background:"white",color:"#14343b",padding:20,borderRadius:16,boxShadow:"0 8px 40px #1235",width:340,maxWidth:"100%",maxHeight:"70vh",overflowY:"auto"}}><h2>Â¿CÃ³mo uso Socratia?</h2><p>GuÃ­a local del producto, sin gastar tokens.</p><div>{["Subir documento","Generar preguntas","Generar diapositivas","Activar avisos"].map(text=><button className="button" type="button" key={text} disabled={busy} onClick={()=>void ask(text)}>{text}</button>)}</div><label><input type="checkbox" checked={useAI} onChange={e=>setUseAI(e.target.checked)}/> Explicar con IA (usa cuota si no hay modelo propio conectado)</label><form onSubmit={e=>{e.preventDefault();void ask(question);}}><label htmlFor="product-question">Â¿En quÃ© paso necesitas ayuda?</label><input id="product-question" value={question} maxLength={600} onChange={e=>setQuestion(e.target.value)} style={{width:"100%",padding:10}}/><button className="button" disabled={busy||question.trim().length<2}>{busy?"Buscando orientaciÃ³nâ€¦":"Consultar"}</button></form>{reply&&<div role="status"><p>{reply.answer}</p><small>{reply.engine?.startsWith("guia_local")?"Guía local del producto":reply.engine==="modelo_propio"?"Modelo propio":"Asistente con IA"}</small><Link href={reply.url}>Ir a ese apartado</Link></div>}</section>}
 <button className="button button-primary" type="button" aria-expanded={open} onClick={()=>setOpen(!open)}>{open?"Cerrar ayuda":"Ayuda con Socratia"}</button></div>;
}

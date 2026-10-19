"use client";
import {useEffect,useState,type ReactNode} from "react";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {ShieldCheck} from "lucide-react";
import {getCurrentUser} from "@/features/auth/api";
import {ApiError} from "@/lib/api";
export function AdminAccess({children}:{children:ReactNode}) {
  const router=useRouter();
  const [status,setStatus]=useState<"loading"|"allowed"|"denied"|"error">("loading");
  const [attempt,setAttempt]=useState(0);
  useEffect(() => {
    let active=true;
    getCurrentUser().then(user => {if (active) setStatus(user.roles.some(role => ["administrator","admin"].includes(role.toLowerCase())) ? "allowed" : "denied");}).catch(err => {
      if (!active) return;
      if (err instanceof ApiError && err.status===401) router.replace("/login");
      else setStatus("error");
    });
    return () => {active=false;};
  },[router,attempt]);
  if (status==="allowed") return children;
  return <main className="admin-access-state">{status==="loading" ? <><div className="loading-orbit"/><p>Comprobando acceso…</p></> : <><ShieldCheck size={34}/><h1>{status==="denied" ? "Este espacio es para administradores" : "No pudimos comprobar tu acceso"}</h1><p>{status==="denied" ? "Continúa tu preparación desde el panel de estudiante." : "Revisa tu conexión y vuelve a intentarlo."}</p>{status==="error" && <button className="button button-primary" onClick={() => {setStatus("loading"); setAttempt(value=>value+1);}}>Reintentar</button>}<Link className="button button-ghost" href="/dashboard">Ir a mi preparación</Link></>}</main>;
}

"use client";

import {useEffect, useRef, useState} from "react";
import {apiRequest} from "@/lib/api";
import {chatHistory, engineLabel, type ChatMessage, type ChatReply} from "@/lib/product-chat";

const shortcuts = ["¿Qué es una hipótesis?", "Ayúdame a defender mi metodología", "¿Cómo explico mis resultados?"];

export function ProductChatbot({open}: {open: boolean}) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("local");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const inFlight = useRef(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) end.current?.scrollIntoView({block: "nearest"});
  }, [messages, busy, open]);

  async function ask(value: string) {
    const text = value.trim();
    if (inFlight.current || text.length < 2) return;
    inFlight.current = true;
    setBusy(true);
    const history = chatHistory(messages);
    setMessages(previous => [...previous.slice(-23), {role: "user", content: text}]);
    setQuestion("");
    try {
      const reply = await apiRequest<ChatReply>("/help/chat", {
        method: "POST",
        body: JSON.stringify({question: text, platform: "web", local_only: mode === "local", history}),
      });
      setMessages(previous => [...previous, {role: "assistant", content: reply.answer, reply, failed: reply.engine === "modelo_no_disponible" || reply.engine === "modelo_no_configurado"}]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Revisa tu conexión y sesión.";
      setMessages(previous => [...previous, {role: "assistant", content: `No pude responder. ${detail} Puedes volver a preguntar o abrir la Guía de uso.`, failed: true}]);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return <div style={{position: "fixed", right: 16, bottom: 72, zIndex: 70, maxWidth: "calc(100vw - 32px)"}}>
    {open && <section id="socratia-chat" aria-label="Chat de Socratia" style={{background: "white", color: "#14343b", borderRadius: 20, boxShadow: "0 8px 40px #1235", width: 380, maxWidth: "calc(100vw - 32px)", maxHeight: "78dvh", display: "flex", flexDirection: "column", overflow: "hidden", marginBottom: 10}}>
      <header style={{padding: "16px 20px", borderBottom: "1px solid #dce9e5", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12}}>
        <div><h2 style={{margin: 0, fontSize: 20}}>Chat de Socratia</h2><small>Te acompaño en tu preparación</small></div>
        <button type="button" disabled={busy || messages.length === 0} onClick={() => setMessages([])} style={{fontSize: 12}}>Nuevo chat</button>
      </header>
      <div role="log" aria-label="Conversación" aria-live="polite" aria-relevant="additions" style={{overflowY: "auto", padding: 16, minHeight: 130, flex: 1}}>
        <p style={{marginTop: 0}}>Hola. Puedo responder dudas generales y ayudarte con tu investigación o defensa. No leo tus documentos automáticamente: puedes compartir un extracto en el mensaje. Para aprender a usar la aplicación, abre la Guía.</p>
        {messages.map((message, index) => <article key={index} style={{margin: "12px 0", marginLeft: message.role === "user" ? 24 : 0, marginRight: message.role === "assistant" ? 12 : 0, padding: 12, borderRadius: 14, background: message.role === "user" ? "#dcefe9" : "#f1f5f4", whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>
          <strong style={{fontSize: 12}}>{message.role === "user" ? "Tú" : "Socratia"}</strong>
          <p style={{margin: "6px 0"}}>{message.content}</p>
          {message.reply?.explanation && <p style={{margin: "8px 0"}}>{message.reply.explanation}</p>}
          {message.reply && <small>{engineLabel(message.reply.engine)}</small>}
        </article>)}
        {busy && <p role="status">Preparando una respuesta para ti…</p>}
        <div ref={end}/>
      </div>
      <div style={{padding: 16, borderTop: "1px solid #dce9e5"}}>
        {messages.length === 0 && <div style={{display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12}}>{shortcuts.map(text => <button className="button" type="button" key={text} disabled={busy} onClick={() => void ask(text)} style={{fontSize: 12}}>{text}</button>)}</div>}
        <label htmlFor="chat-engine" style={{fontSize: 12}}>Cómo responder</label>
        <select id="chat-engine" value={mode} disabled={busy} onChange={event => setMode(event.target.value)} style={{display: "block", width: "100%", padding: 8, marginBottom: 8, background: "white", color: "#14343b"}}>
          <option value="local">IA propia · si está conectada</option>
          <option value="configured">IA disponible · puede usar cuota externa</option>
        </select>
        <form onSubmit={event => {event.preventDefault(); void ask(question);}}>
          <label htmlFor="chatbot-question" style={{fontSize: 12}}>Escribe tu mensaje</label>
          <textarea id="chatbot-question" value={question} maxLength={600} rows={2} disabled={busy} onChange={event => setQuestion(event.target.value)} placeholder="Por ejemplo: ¿cómo explico mi metodología?" style={{display: "block", width: "100%", padding: 10, border: "1px solid #b7cbc5", borderRadius: 10, resize: "vertical", background: "white", color: "#14343b"}}/>
          <button className="button button-primary" type="submit" disabled={busy || question.trim().length < 2} style={{width: "100%", marginTop: 8}}>{busy ? "Respondiendo…" : "Enviar mensaje"}</button>
        </form>
        <small>Historial temporal. El chatbot puede equivocarse; contrasta sus respuestas.</small>
      </div>
    </section>}
  </div>;
}

export type ChatReply = {answer: string; explanation?: string; url: string; engine?: string; platform?: string};
export type ChatMessage = {role: "user" | "assistant"; content: string; reply?: ChatReply; failed?: boolean};

export function chatHistory(messages: ChatMessage[]) {
  return messages.filter(message => !message.failed).slice(-8).map(message => ({
    role: message.role,
    content: [message.content, message.reply?.explanation].filter(Boolean).join("\n").slice(0, 1200),
  }));
}

export function engineLabel(engine?: string) {
  if (engine === "modelo_no_configurado") return "Modelo propio de conversación sin conectar";
  if (engine === "modelo_no_disponible") return "El chatbot no completó una respuesta";
  if (engine === "modelo_propio") return "IA propia · modelo de conversación";
  if (engine === "groq") return "IA externa · proveedor configurado";
  if (engine === "guia_local_modelo_no_configurado") return "El modelo de conversación propio no está conectado. Te muestro la guía verificada; no se llamó a una IA externa.";
  if (engine === "guia_local_ia_no_disponible") return "La IA no completó la respuesta. Te muestro la guía verificada.";
  return "Guía verificada del producto · sin inferencia de IA";
}

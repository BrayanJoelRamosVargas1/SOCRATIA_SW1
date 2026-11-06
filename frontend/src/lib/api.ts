import { API_URL } from "@/lib/config";

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
    fields?: Array<{ field: string; message: string }>;
  };
  detail?: unknown;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "request_failed",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = {};
  try {
    const parsed:unknown = await response.json();
    if(parsed && typeof parsed === "object" && !Array.isArray(parsed)) payload=parsed as ApiErrorPayload;
  } catch {
    // The fallback below handles empty and non-JSON responses.
  }
  const candidate = payload.error?.message ?? payload.detail;
  const defaults: Record<number,string> = {
    401:"Tu sesión terminó. Inicia sesión nuevamente.",403:"No tienes permiso para realizar esta acción.",
    404:"No se encontró el recurso solicitado.",405:"Esta acción no está disponible.",
    409:"La solicitud entra en conflicto con el estado actual. Actualiza la página.",
    422:"Revisa los datos enviados.",429:"Se alcanzó el límite de solicitudes. Espera un momento y vuelve a intentar.",
    500:"El servidor no pudo completar la solicitud.",502:"No pudimos conectar con el servicio. Inténtalo nuevamente.",
    503:"El servicio no está disponible temporalmente.",504:"El servicio tardó demasiado en responder.",
  };
  const english = /^(denied|not |invalid |missing |incorrect |unauthor|forbidden|internal server|request |field required|value error|input should|database |method not|too many|service unavailable|unprocessable|bad gateway|gateway timeout|failed |an error|could not|network error|(?:gemini|groq) (?:returned|is |failed|rejected|could))/i;
  const message = typeof candidate === "string" && candidate.trim() && !english.test(candidate.trim())
    ? candidate : defaults[response.status] ?? "No se pudo completar la solicitud.";
  return new ApiError(
    message,
    response.status,
    payload.error?.code,
  );
}

async function execute<T>(path: string, options: RequestInit): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  }); } catch(error) {
    if(error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError("No pudimos conectar con el servidor. Revisa tu conexión e inténtalo nuevamente.",0,"network_error");
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

let sessionRefresh: Promise<unknown> | null = null;
const readCache = new Map<string,{value:unknown;expires:number}>();
const readPending = new Map<string,Promise<unknown>>();
let cacheEpoch = 0;
const SESSION_EVENT = "socratia.session.changed";

export function invalidateReadCache() {
  cacheEpoch++;
  readCache.clear();
  readPending.clear();
}

if(typeof window!=="undefined" && typeof window.addEventListener==="function") {
  window.addEventListener("storage",event=>{if(event.key===SESSION_EVENT)invalidateReadCache();});
  window.addEventListener("pageshow",event=>{if(event.persisted)invalidateReadCache();});
}

function announceSessionChange() {
  try {window.localStorage.setItem(SESSION_EVENT,`${Date.now()}:${Math.random()}`);} catch { /* storage can be disabled */ }
}

function cacheableRead(path:string,options:RequestInit) {
  // Browser memory only: never share private data through the Next server or disk.
  return typeof window!=="undefined" && !options.signal && !options.headers && options.cache!=="no-store"
    && ["/profile","/documents","/simulations","/subscription"].some(value=>value===path);
}

export async function apiUpload<T>(path:string,body:FormData,onProgress?:(percent:number)=>void):Promise<T> {
  invalidateReadCache();
  const send=()=>new Promise<T>((resolve,reject)=>{
    const request=new XMLHttpRequest();
    request.open("POST",`${API_URL}${path}`);
    request.withCredentials=true;
    request.timeout=120000;
    request.upload.onprogress=event=>{if(event.lengthComputable)onProgress?.(Math.round(event.loaded/event.total*100));};
    request.onerror=()=>reject(new ApiError("Se interrumpió la conexión durante la subida. Puedes reintentar.",0));
    request.ontimeout=()=>reject(new ApiError("La subida tardó demasiado. Revisa tu conexión.",0));
    request.onload=async()=>{
      if(request.status<200 || request.status>=300){
        reject(await parseError(new Response(request.responseText,{status:request.status||502})));
        return;
      }
      try {resolve(JSON.parse(request.responseText) as T);}
      catch {reject(new ApiError("El servidor devolvió una respuesta incompleta.",502));}
    };
    request.send(body);
  });
  try {return await send();}
  catch(error){
    if(!(error instanceof ApiError) || error.status!==401)throw error;
    if(!sessionRefresh)sessionRefresh=execute("/auth/refresh",{method:"POST"}).finally(()=>{sessionRefresh=null;});
    await sessionRefresh;
    return await send();
  } finally {invalidateReadCache();}
}

async function requestWithSession<T>(
  path: string,
  options: RequestInit = {},
  retrySession = true,
): Promise<T> {
  try {
    return await execute<T>(path, options);
  } catch (error) {
    const mayRefresh =
      retrySession &&
      error instanceof ApiError &&
      error.status === 401 &&
      !path.startsWith("/auth/");
    if(error instanceof ApiError && error.status===401)invalidateReadCache();
    if (!mayRefresh) {
      throw error;
    }
    if (!sessionRefresh) {
      sessionRefresh = execute("/auth/refresh", { method: "POST" }).finally(() => {
        sessionRefresh = null;
      });
    }
    await sessionRefresh;
    return execute<T>(path, options);
  }
}

export function apiRequest<T>(path:string,options:RequestInit={},retrySession=true):Promise<T> {
  const method=(options.method??"GET").toUpperCase();
  if(method!=="GET") {
    invalidateReadCache();
    return requestWithSession<T>(path,options,retrySession).then(value=>{
      if(["/auth/login","/auth/logout","/auth/register"].includes(path))announceSessionChange();
      return value;
    }).finally(invalidateReadCache);
  }
  if(!cacheableRead(path,options))return requestWithSession<T>(path,options,retrySession);
  const cached=readCache.get(path);
  if(cached && cached.expires>Date.now())return Promise.resolve(cached.value as T);
  const pending=readPending.get(path);
  if(pending)return pending as Promise<T>;
  const epoch=cacheEpoch;
  const request=requestWithSession<T>(path,options,retrySession).then(value=>{
    if(epoch===cacheEpoch)readCache.set(path,{value,expires:Date.now()+10000});
    return value;
  }).finally(()=>{if(readPending.get(path)===request)readPending.delete(path);});
  readPending.set(path,request);
  return request;
}

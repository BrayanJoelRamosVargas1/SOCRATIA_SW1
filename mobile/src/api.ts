import { CapacitorHttp } from '@capacitor/core';
import { DEFAULT_SERVER, apiPath } from './policy.mjs';

let refresh: Promise<unknown> | null = null;
export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
export async function api<T>(path: string, method = 'GET', data?: unknown, retry = true): Promise<T> {
  let response;
  try {
    response = await CapacitorHttp.request({url: DEFAULT_SERVER + apiPath(path), method,
      headers: {'Content-Type':'application/json'}, data, connectTimeout:15000, readTimeout:30000});
  } catch { throw new ApiError('No pudimos conectar. Revisa Internet y vuelve a intentar.', 0); }
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    refresh ??= api('/auth/refresh', 'POST', undefined, false).finally(() => { refresh = null; });
    await refresh;
    return api<T>(path, method, data, false);
  }
  if (response.status < 200 || response.status >= 300) {
    const defaults: Record<number,string> = {401:'Inicia sesión para continuar.',403:'No tienes permiso.',404:'Este material todavía no está disponible.',429:'Espera un momento antes de volver a intentar.',503:'Este servicio todavía no está configurado.'};
    throw new ApiError(defaults[response.status] ?? 'No pudimos completar la solicitud. Intenta nuevamente.', response.status);
  }
  return response.data as T;
}

export async function exportFile(documentId: string, kind: 'questions' | 'presentation') {
  const { Filesystem, Directory } = await import('@capacitor/filesystem');
  const { Share } = await import('@capacitor/share');
  // Validate session and rotate cookies before requesting the binary export.
  await api('/profile');
  const response = await CapacitorHttp.get({url: DEFAULT_SERVER + apiPath(`/documents/${documentId}/${kind}/export`), responseType:'arraybuffer', connectTimeout:15000, readTimeout:60000});
  if (response.status !== 200 || typeof response.data !== 'string') throw new Error('No se pudo descargar el material.');
  if (response.data.length > 14_000_000) throw new Error('Este material es grande. Descárgalo desde la web.');
  const path = `socratia-${documentId}-${kind}.${kind === 'questions' ? 'pdf' : 'pptx'}`;
  const file = await Filesystem.writeFile({path, data:response.data, directory:Directory.Cache});
  await Share.share({title:'Material de Socratia', files:[file.uri], dialogTitle:'Guardar o compartir material'});
}

import { PushNotifications } from '@capacitor/push-notifications';
import { api } from './api';
import { safeNotificationDocument } from './policy.mjs';
let token: string | null = null;
const preference = 'socratia.notifications.enabled';
function remember(enabled: boolean) { try { localStorage.setItem(preference, String(enabled)); } catch { /* Optional preference; never stores tokens. */ } }
function desired() { try { return localStorage.getItem(preference); } catch { return null; } }
export async function initializePush(onDocument: (id: string | null) => void, announce: (message: string) => void) {
  await PushNotifications.createChannel({id:'socratia_preparation',name:'Tu preparación',description:'Materiales y resultados de Socratia',importance:4,visibility:0,vibration:true});
  await PushNotifications.addListener('pushNotificationReceived', () => announce('Tu preparación tiene novedades. Actualiza tus documentos.'));
  await PushNotifications.addListener('pushNotificationActionPerformed', action => {
    const id = safeNotificationDocument(action.notification.data?.url);
    if (id) onDocument(id);
    else if (action.notification.data?.url === '/documents') onDocument(null);
  });
}
async function currentToken(): Promise<string> {
  if (token) return token;
  let success: Awaited<ReturnType<typeof PushNotifications.addListener>> | undefined;
  let failure: typeof success;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    return await new Promise<string>((resolve, reject) => {
      timeout = setTimeout(() => reject(new Error('No pudimos conectar los avisos. Revisa Internet y vuelve a intentar.')), 15000);
      void (async () => {
        success = await PushNotifications.addListener('registration', value => { token = value.value; resolve(value.value); });
        failure = await PushNotifications.addListener('registrationError', () => reject(new Error('No pudimos activar los avisos en este celular. Vuelve a intentar.')));
        await PushNotifications.register();
      })().catch(reject);
    });
  } finally { clearTimeout(timeout); await success?.remove(); await failure?.remove(); }
}
export async function enablePush(requestPermission = true) {
  const config = await api<{enabled:boolean}>('/push/native');
  if (!config.enabled) throw new Error('Los avisos no están disponibles por el momento. Inténtalo más tarde.');
  let permission = await PushNotifications.checkPermissions();
  if (permission.receive === 'prompt' && requestPermission) permission = await PushNotifications.requestPermissions();
  if (permission.receive !== 'granted') throw new Error('Activa el permiso de notificaciones en los ajustes del celular.');
  await api('/push/native', 'POST', {token:await currentToken()});
  remember(true);
}
export async function getPushState(): Promise<{available: boolean; enabled: boolean}> {
  const config = await api<{enabled:boolean}>('/push/native');
  if (!config.enabled) return {available:false,enabled:false};
  if (desired() === 'false' || (await PushNotifications.checkPermissions()).receive !== 'granted') return {available:true,enabled:false};
  const state = await api<{registered:boolean}>('/push/native/status','POST',{token:await currentToken()});
  if (state.registered) remember(true);
  return {available:true,enabled:state.registered};
}
export async function restorePush() {
  if (desired() === 'true') await enablePush(false);
}
export async function disablePush() {
  if (!token && (await PushNotifications.checkPermissions()).receive === 'granted') token = await currentToken();
  if (token) await api('/push/native', 'DELETE', {token});
  remember(false);
  await PushNotifications.unregister();
  token = null;
}

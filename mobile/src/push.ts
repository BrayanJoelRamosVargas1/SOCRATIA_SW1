import { PushNotifications } from '@capacitor/push-notifications';
import { api } from './api';
import { safeNotificationDocument } from './policy.mjs';
let token: string | null = null;
export async function initializePush(onDocument: (id: string) => void, announce: (message: string) => void) {
  await PushNotifications.addListener('pushNotificationReceived', () => announce('Tu preparación tiene novedades. Actualiza tus documentos.'));
  await PushNotifications.addListener('pushNotificationActionPerformed', action => {
    const id = safeNotificationDocument(action.notification.data?.url);
    if (id) onDocument(id);
  });
}
async function currentToken(): Promise<string> {
  let success: Awaited<ReturnType<typeof PushNotifications.addListener>> | undefined;
  let failure: typeof success;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    return await new Promise<string>((resolve, reject) => {
      timeout = setTimeout(() => reject(new Error('No se pudo registrar el celular. Revisa Firebase y la conexión.')), 15000);
      void (async () => {
        success = await PushNotifications.addListener('registration', value => { token = value.value; resolve(value.value); });
        failure = await PushNotifications.addListener('registrationError', () => reject(new Error('No se pudieron activar los avisos. Revisa Firebase.')));
        await PushNotifications.register();
      })().catch(reject);
    });
  } finally { clearTimeout(timeout); await success?.remove(); await failure?.remove(); }
}
export async function enablePush() {
  const config = await api<{enabled:boolean}>('/push/native');
  if (!config.enabled) throw new Error('Los avisos de la APK requieren completar la configuración de Firebase en el servidor.');
  let permission = await PushNotifications.checkPermissions();
  if (permission.receive === 'prompt') permission = await PushNotifications.requestPermissions();
  if (permission.receive !== 'granted') throw new Error('Activa el permiso de notificaciones en los ajustes del celular.');
  await api('/push/native', 'POST', {token:await currentToken()});
}
export async function disablePush() {
  if (!token && (await PushNotifications.checkPermissions()).receive === 'granted') token = await currentToken();
  if (token) await api('/push/native', 'DELETE', {token});
  await PushNotifications.unregister();
  token = null;
}

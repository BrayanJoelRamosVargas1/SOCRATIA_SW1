export const DEFAULT_SERVER = 'https://socratia.54.221.46.202.sslip.io';
// A build may replace this constant when the pilot changes address. No arbitrary endpoints in the UI.
export function apiPath(path) {
  if (!/^\/(auth\/(login|refresh|logout)|profile|documents(?:\/[a-zA-Z0-9-]+(?:\/(questions(?:\/export)?|presentation(?:\/export)?))?)?|simulations(?:\/[a-zA-Z0-9-]+\/evaluation)?|push\/(native(?:\/test)?))$/.test(path)) {
    throw new Error('Esta función se utiliza desde la versión web.');
  }
  return `/api/v1${path}`;
}
export function safeNotificationDocument(value) {
  const match = typeof value === 'string' && value.match(/^\/documents\/([a-zA-Z0-9-]+)$/);
  return match ? match[1] : null;
}

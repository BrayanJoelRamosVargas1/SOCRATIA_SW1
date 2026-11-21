export const DEFAULT_SERVER = 'https://socratia.54.221.46.202.sslip.io';
export function serverOrigin(value){
  const parsed=new URL(value);
  if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.pathname!=='/'||parsed.search||parsed.hash)throw new Error('Configura un origen HTTPS de Socratia válido.');
  return parsed.origin;
}
// A build may replace this constant when the pilot changes address. No arbitrary endpoints in the UI.
export function apiPath(path, method = 'GET') {
  if (!/^\/(help\/ask|auth\/(login|refresh|logout)|profile|documents(?:\/[a-zA-Z0-9-]+(?:\/(questions(?:\/export)?|presentation(?:\/export)?))?)?|simulations(?:\/[a-zA-Z0-9-]+\/evaluation)?|push\/(native(?:\/(?:test|status))?))$/.test(path)) {
    throw new Error('Esta función se utiliza desde la versión web.');
  }
  const allowed = path.startsWith('/auth/') || path === '/help/ask' ? ['POST']
    : path === '/push/native' ? ['GET', 'POST', 'DELETE']
    : ['/push/native/test','/push/native/status'].includes(path) ? ['POST'] : ['GET'];
  if (!allowed.includes(method.toUpperCase())) throw new Error('Esta función se utiliza desde la versión web.');
  return `/api/v1${path}`;
}
export function helpDestination(path) {
  const internal={'/documents':'documents','/history':'results','/mobile/results':'results','/profile':'account','/mobile/account':'account'};
  if(Object.hasOwn(internal,path))return {web:false,section:internal[path]};
  if(['/forgot-password','/register','/login','/simulations/new'].includes(path))return {web:true,section:''};
  return null;
}
export function safeNotificationDocument(value) {
  const match = typeof value === 'string' && value.match(/^\/documents\/([a-zA-Z0-9-]+)$/);
  return match ? match[1] : null;
}

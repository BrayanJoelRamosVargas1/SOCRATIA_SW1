type Preferences = {mode?:"voice"|"text"; cameraEnabled?:boolean; autoListen?:boolean; appearanceContinuous?:boolean};
const key = (id:string) => `socratia.defense.preferences.v1:${id}`;

// Tab-local preferences contain no audio, images, transcript or credentials.
export function readSessionPreferences(id:string):Preferences {
  try {
    const value:unknown = JSON.parse(window.sessionStorage.getItem(key(id)) ?? '{}');
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    const record = value as Record<string,unknown>;
    return {
      ...(record.mode === 'voice' || record.mode === 'text' ? {mode:record.mode} : {}),
      ...(typeof record.cameraEnabled === 'boolean' ? {cameraEnabled:record.cameraEnabled} : {}),
      ...(typeof record.autoListen === 'boolean' ? {autoListen:record.autoListen} : {}),
      ...(typeof record.appearanceContinuous === 'boolean' ? {appearanceContinuous:record.appearanceContinuous} : {}),
    };
  } catch { return {}; }
}

export function saveSessionPreferences(id:string, patch:Preferences) {
  try { window.sessionStorage.setItem(key(id), JSON.stringify({...readSessionPreferences(id),...patch})); }
  catch { /* Private browsing/storage restrictions must not interrupt a defense. */ }
}

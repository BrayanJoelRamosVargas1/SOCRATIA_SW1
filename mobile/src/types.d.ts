declare module '*.mjs' {
  export const DEFAULT_SERVER: string;
  export function serverOrigin(value:string):string;
  export function apiPath(path: string, method?: string): string;
  export function safeNotificationDocument(value: unknown): string | null;
  export function helpDestination(path: unknown): {web:boolean;section:string} | null;
}
interface ImportMeta {readonly env: {readonly VITE_SOCRATIA_SERVER_URL?:string}}

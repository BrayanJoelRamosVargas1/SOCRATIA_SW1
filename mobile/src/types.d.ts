declare module '*.mjs' {
  export const DEFAULT_SERVER: string;
  export function apiPath(path: string, method?: string): string;
  export function safeNotificationDocument(value: unknown): string | null;
}

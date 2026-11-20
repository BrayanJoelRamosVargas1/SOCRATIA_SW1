declare module '*.mjs' {
  export const DEFAULT_SERVER: string;
  export function apiPath(path: string): string;
  export function safeNotificationDocument(value: unknown): string | null;
}

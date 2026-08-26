import { API_URL } from "@/lib/config";

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
    fields?: Array<{ field: string; message: string }>;
  };
  detail?: string;
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
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    // The fallback below handles empty and non-JSON responses.
  }
  return new ApiError(
    payload.error?.message ?? payload.detail ?? "No se pudo completar la solicitud.",
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
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function apiRequest<T>(
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
    if (!mayRefresh) {
      throw error;
    }
    await execute("/auth/refresh", { method: "POST" });
    return execute<T>(path, options);
  }
}

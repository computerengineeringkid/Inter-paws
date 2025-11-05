export interface ApiError extends Error {
  status?: number;
  data?: unknown;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error: ApiError = new Error(response.statusText);
    error.status = response.status;
    try {
      error.data = await response.json();
    } catch (err) {
      error.data = await response.text();
    }
    throw error;
  }

  try {
    return (await response.json()) as T;
  } catch (err) {
    return {} as T;
  }
}

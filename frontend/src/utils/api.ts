// frontend/src/utils/api.ts

async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.error || `HTTP error! status: ${response.status}`
    );
  }
  return response.json();
}

export async function apiFetch(url: string, options: RequestInit = {}) {
  const defaultHeaders = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });
  return handleResponse(response);
}

export async function apiFetchWithBody(
  url: string,
  method: "POST" | "PUT" | "DELETE",
  body: unknown
) {
  return apiFetch(url, {
    method,
    body: JSON.stringify(body),
  });
}

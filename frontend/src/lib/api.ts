import {
  clearAccessToken,
  getAccessToken,
} from "@/lib/auth";


const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";


export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options?.headers);

  if (!headers.has("Content-Type")) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`,
    );
  }

  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      ...options,
      headers,
    },
  );

  if (!response.ok) {
    let message = `Erreur HTTP ${response.status}`;

    try {
      const error: unknown = await response.json();

      if (
        typeof error === "object" &&
        error !== null &&
        "detail" in error &&
        typeof error.detail === "string"
      ) {
        message = error.detail;
      }
    } catch {
      // La réponse ne contient pas de JSON exploitable.
    }

    if (
      response.status === 401 &&
      endpoint !== "/auth/login"
    ) {
      clearAccessToken();

      if (typeof window !== "undefined") {
        window.location.replace("/login");
      }
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

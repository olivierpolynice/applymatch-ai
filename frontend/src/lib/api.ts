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


export async function downloadApiFile(
  endpoint: string,
  filename: string,
): Promise<void> {
  const token = getAccessToken();
  const headers = new Headers();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${endpoint}`, { headers });

  if (!response.ok) {
    throw new Error(`Téléchargement impossible : HTTP ${response.status}`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

const ACCESS_TOKEN_KEY = "applymatch_access_token";
const AUTH_CHANGE_EVENT = "applymatch-auth-change";

interface AccessTokenPayload {
  exp?: number;
  sub?: string;
  type?: string;
}

function decodeAccessToken(
  token: string,
): AccessTokenPayload | null {
  try {
    const encodedPayload = token.split(".")[1];

    if (!encodedPayload) {
      return null;
    }

    const normalizedPayload = encodedPayload
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(
        Math.ceil(encodedPayload.length / 4) * 4,
        "=",
      );

    return JSON.parse(
      window.atob(normalizedPayload),
    ) as AccessTokenPayload;
  } catch {
    return null;
  }
}

function notifyAuthChange() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new Event(AUTH_CHANGE_EVENT),
    );
  }
}

export function setAccessToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    ACCESS_TOKEN_KEY,
    token,
  );
  notifyAuthChange();
}

export function clearAccessToken() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(
    ACCESS_TOKEN_KEY,
  );
  notifyAuthChange();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const token = window.sessionStorage.getItem(
    ACCESS_TOKEN_KEY,
  );

  if (!token) {
    return null;
  }

  const payload = decodeAccessToken(token);
  const expiresAt = (payload?.exp ?? 0) * 1000;

  if (
    payload?.type !== "access" ||
    expiresAt <= Date.now()
  ) {
    window.sessionStorage.removeItem(
      ACCESS_TOKEN_KEY,
    );
    return null;
  }

  return token;
}

export function getAccessTokenExpiration(): number | null {
  const token = getAccessToken();

  if (!token) {
    return null;
  }

  const payload = decodeAccessToken(token);

  return payload?.exp
    ? payload.exp * 1000
    : null;
}

export function hasValidAccessToken(): boolean {
  return getAccessToken() !== null;
}

export function subscribeToAuth(
  onChange: () => void,
) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  window.addEventListener(
    AUTH_CHANGE_EVENT,
    onChange,
  );
  window.addEventListener("storage", onChange);

  return () => {
    window.removeEventListener(
      AUTH_CHANGE_EVENT,
      onChange,
    );
    window.removeEventListener("storage", onChange);
  };
}

export function getAuthSnapshot(): boolean {
  return hasValidAccessToken();
}

export function getServerAuthSnapshot(): boolean {
  return false;
}

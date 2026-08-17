import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";


afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});


export function createAccessToken(
  expiresAt: number,
): string {
  const header = window.btoa(
    JSON.stringify({ alg: "HS256", typ: "JWT" }),
  );
  const payload = window.btoa(
    JSON.stringify({
      sub: "1",
      type: "access",
      exp: Math.floor(expiresAt / 1000),
    }),
  );

  return `${header}.${payload}.signature`;
}

"use client";

import { useRouter } from "next/navigation";
import {
  type ReactNode,
  useEffect,
  useSyncExternalStore,
} from "react";

import {
  clearAccessToken,
  getAccessTokenExpiration,
  getAuthSnapshot,
  getServerAuthSnapshot,
  subscribeToAuth,
} from "@/lib/auth";


interface AuthGuardProps {
  children: ReactNode;
}


export default function AuthGuard({
  children,
}: AuthGuardProps) {
  const router = useRouter();
  const isAuthenticated = useSyncExternalStore(
    subscribeToAuth,
    getAuthSnapshot,
    getServerAuthSnapshot,
  );

  useEffect(() => {
    if (!isAuthenticated) {
      const redirectTimeout = window.setTimeout(() => {
        if (!getAuthSnapshot()) {
          router.replace("/login");
        }
      }, 0);

      return () => window.clearTimeout(
        redirectTimeout,
      );
    }

    const expiresAt = getAccessTokenExpiration();

    if (!expiresAt) {
      clearAccessToken();
      router.replace("/login");
      return;
    }

    const remainingTime = Math.max(
      0,
      expiresAt - Date.now(),
    );
    const timeout = window.setTimeout(() => {
      clearAccessToken();
      router.replace("/login");
    }, remainingTime);

    return () => window.clearTimeout(timeout);
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Vérification de la session...
      </main>
    );
  }

  return children;
}

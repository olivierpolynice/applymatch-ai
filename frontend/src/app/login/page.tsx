"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { apiRequest } from "@/lib/api";
import {
  hasValidAccessToken,
  setAccessToken,
} from "@/lib/auth";


interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}


export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasValidAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await apiRequest<TokenResponse>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
          }),
        },
      );

      setAccessToken(response.access_token);
      router.replace("/");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Connexion impossible",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
          ApplyMatch AI
        </p>

        <h1 className="mt-3 text-3xl font-bold">
          Connexion administrateur
        </h1>

        <p className="mt-3 text-sm text-slate-400">
          Connecte-toi pour accéder au tableau de bord et aux actions sensibles.
        </p>

        {error && (
          <p className="mt-5 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">
            {error}
          </p>
        )}

        <form
          onSubmit={submit}
          className="mt-6 grid gap-5"
        >
          <label className="grid gap-2 text-sm font-medium">
            Adresse e-mail
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-cyan-400"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium">
            Mot de passe
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-cyan-400"
            />
          </label>

          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-lg bg-cyan-500 px-4 py-3 font-bold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting
              ? "Connexion..."
              : "Se connecter"}
          </button>
        </form>
      </section>
    </main>
  );
}

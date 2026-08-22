"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";


export default function GlobalError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      Sentry.captureException(error);
    }
  }, [error]);

  return (
    <html lang="fr">
      <body className="bg-slate-950 text-slate-100">
        <main className="mx-auto max-w-xl px-6 py-24 text-center">
          <h1 className="text-2xl font-bold">Une erreur inattendue est survenue</h1>
          <p className="mt-4 text-slate-400">
            Recharge la page. Si le problème continue, il sera visible dans la surveillance ApplyMatch.
          </p>
        </main>
      </body>
    </html>
  );
}

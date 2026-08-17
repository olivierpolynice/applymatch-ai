"use client";

import { useRouter } from "next/navigation";

import { clearAccessToken } from "@/lib/auth";


export default function LogoutButton() {
  const router = useRouter();

  function logout() {
    clearAccessToken();
    router.replace("/login");
  }

  return (
    <button
      type="button"
      onClick={logout}
      className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-red-700 hover:text-red-300"
    >
      Se déconnecter
    </button>
  );
}

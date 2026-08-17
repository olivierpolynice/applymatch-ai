# Installation de l’authentification frontend

Copier les fichiers dans le projet `frontend` en conservant l’arborescence.

Dans `src/app/page.tsx`, ajouter les imports :

```tsx
import AuthGuard from "@/components/AuthGuard";
import LogoutButton from "@/components/LogoutButton";
```

Entourer tout le contenu retourné par la page :

```tsx
return (
  <AuthGuard>
    <main>{/* contenu actuel */}</main>
  </AuthGuard>
);
```

Placer le bouton dans le `header` du dashboard :

```tsx
<LogoutButton />
```

Vérifier `frontend/.env.local` :

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Enfin lancer :

```powershell
npm run lint
npm run build
```

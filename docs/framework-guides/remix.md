# Remix + Challenge Tokens

## The Problem

Remix loaders and actions run on the server. Like Next.js SSR, the server doesn't have the user's challenge cookies, so server-side data fetches get challenged.

## Solution

### 1. Forward cookies in loaders

```javascript
export async function loader({ request }) {
  const cookie = request.headers.get("Cookie") || "";
  const res = await fetch("https://api.yoursite.com/data", {
    headers: { Cookie: cookie },
  });

  if (res.status === 403) {
    throw redirect("/challenge?return=" + new URL(request.url).pathname);
  }

  return json(await res.json());
}
```

### 2. Forward cookies in actions

```javascript
export async function action({ request }) {
  const cookie = request.headers.get("Cookie") || "";
  const formData = await request.formData();

  const res = await fetch("https://api.yoursite.com/submit", {
    method: "POST",
    headers: {
      Cookie: cookie,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(Object.fromEntries(formData)),
  });

  if (res.status === 403) {
    throw redirect("/challenge?return=" + new URL(request.url).pathname);
  }

  return json(await res.json());
}
```

### 3. Add the challenge SDK to your root layout

```javascript
// app/root.tsx
export default function App() {
  return (
    <html>
      <head>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer />
      </head>
      <body><Outlet /></body>
    </html>
  );
}
```

## Verification

```bash
challenge-validator test https://yoursite.com --token <token>
```

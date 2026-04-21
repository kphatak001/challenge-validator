# Next.js SSR + Challenge Tokens

## The Problem

Next.js server-side rendering (SSR) makes requests from the server, not the browser. The server doesn't have the user's challenge token cookie, so SSR requests get challenged.

## Solution

### 1. Forward cookies in SSR requests

In `getServerSideProps`, forward the user's cookies to your API:

```javascript
export async function getServerSideProps(context) {
  const res = await fetch('https://api.yoursite.com/data', {
    headers: {
      Cookie: context.req.headers.cookie || '',
    },
  });
  const data = await res.json();
  return { props: { data } };
}
```

### 2. Handle challenge responses in SSR

If the API returns a challenge, redirect the user to solve it:

```javascript
export async function getServerSideProps(context) {
  const res = await fetch('https://api.yoursite.com/data', {
    headers: { Cookie: context.req.headers.cookie || '' },
  });

  if (res.status === 403) {
    return {
      redirect: { destination: '/challenge?return=' + context.resolvedUrl, permanent: false },
    };
  }

  return { props: { data: await res.json() } };
}
```

### 3. Exempt SSR server IPs from challenges

If your Next.js server has a static IP or runs in a known environment, allowlist it in your WAF rules so SSR requests aren't challenged.

## Verification

```bash
challenge-validator test https://yoursite.com --token <token> --suite token,cors
```

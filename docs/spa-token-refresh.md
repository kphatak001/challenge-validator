# SPA Token Refresh

## Problem

Your challenge token expires and the single-page app doesn't refresh it, causing users to hit challenge pages mid-session.

## Root Cause

Challenge tokens have a TTL (e.g., 30 minutes for Cloudflare, 2 minutes for reCAPTCHA). SPAs that don't reload the page never trigger the SDK's built-in refresh mechanism.

## Solution

1. **Embed the challenge SDK script on every page**, not just the login page. The SDK handles refresh automatically when loaded.
2. **Set up a background refresh** — poll the challenge endpoint before the token expires:
   ```javascript
   // Refresh token at 80% of TTL
   setInterval(() => {
     // Trigger SDK refresh (vendor-specific)
     // Cloudflare: turnstile.reset()
     // reCAPTCHA: grecaptcha.execute()
   }, TOKEN_TTL_MS * 0.8);
   ```
3. **Handle 403 responses** in your API client — if a request returns a challenge, re-trigger the SDK and retry:
   ```javascript
   async function fetchWithRetry(url, options) {
     const resp = await fetch(url, options);
     if (resp.status === 403) {
       await refreshChallengeToken();
       return fetch(url, options);
     }
     return resp;
   }
   ```

## Verification

Run: `challenge-validator test <url> --token <token> --token-ttl 30`

The `token_refresh` test should now pass.

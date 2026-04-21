# Cookie Cross-Subdomain

## Problem

Challenge token cookies are scoped too narrowly, causing re-challenges when users navigate between subdomains or paths.

## Root Cause

The challenge SDK sets cookies with a specific subdomain (e.g., `www.example.com`) instead of the parent domain (`.example.com`), or with a specific path instead of `/`.

## Solution

1. **Set cookie domain to the parent domain** with a dot prefix:
   - ❌ `Domain=www.example.com` — only works on www
   - ✅ `Domain=.example.com` — works on all subdomains

2. **Set cookie path to `/`**:
   - ❌ `Path=/app` — only works under /app
   - ✅ `Path=/` — works everywhere

3. **Use `SameSite=Lax`** (not `Strict`) if your app makes cross-origin API calls:
   - `Strict` blocks the cookie on any cross-origin navigation
   - `Lax` allows it on top-level navigations (links, form GETs)
   - `None` allows it everywhere (requires `Secure`)

4. **Cloudflare**: Cookie scope is managed automatically. If you see scope issues, check if a custom transform rule is modifying Set-Cookie headers.

5. **AWS WAF**: Configure the token cookie domain in your WAF web ACL settings.

## Verification

Run: `challenge-validator test <url> --suite cookies`

The `cookie_scope` test should now pass.

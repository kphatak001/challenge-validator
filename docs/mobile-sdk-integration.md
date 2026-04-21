# Mobile SDK Integration

## Problem

Native mobile apps can't render HTML challenge pages or execute challenge JavaScript.

## Root Cause

Challenge SDKs are designed for browsers. Mobile apps using raw HTTP clients (URLSession, OkHttp) receive HTML challenge pages they can't process.

## Solution

1. **Use the vendor's native SDK** instead of relying on cookie-based challenges:
   - Cloudflare: Turnstile iOS/Android SDK
   - reCAPTCHA: reCAPTCHA Enterprise Mobile SDK
   - hCaptcha: hCaptcha Android/iOS SDK

2. **Use a WebView for the challenge flow** if no native SDK is available:
   ```swift
   // iOS: Present challenge in a WKWebView
   let webView = WKWebView()
   webView.load(URLRequest(url: challengeURL))
   // Extract token from cookies after challenge completion
   webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
       let token = cookies.first { $0.name == "cf_clearance" }?.value
   }
   ```

3. **Exempt mobile API paths from browser challenges.** Use API key or JWT authentication for mobile endpoints and apply rate-limiting instead of interactive challenges.

4. **Pass the challenge token in a header** instead of a cookie if your mobile HTTP client doesn't support cookie jars:
   ```
   X-Challenge-Token: <token_value>
   ```

## Verification

Test your mobile API endpoint:
```bash
challenge-validator test https://api.yoursite.com/mobile --token <token>
```

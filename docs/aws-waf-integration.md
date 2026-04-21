# AWS WAF Integration Guide

This guide covers the 6 most common issues when integrating AWS WAF Bot Control, CAPTCHA, and Silent Challenge with your application.

---

## 1. CORS Preflight Blocked (TGT_VolumetricIpTokenAbsent)

**The #1 SA escalation for AWS WAF Bot Control.**

### Problem

Browser OPTIONS preflight requests are blocked because they don't carry the `aws-waf-token` cookie. The `TGT_VolumetricIpTokenAbsent` rule in the targeted bot control rule group blocks any request missing a token.

### Root Cause

Browsers never attach cookies to OPTIONS preflight requests (per the CORS spec). The Bot Control rule group doesn't distinguish between "missing token because bot" and "missing token because preflight."

### Fix

Add a scope-down statement to exclude OPTIONS from Bot Control evaluation:

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesBotControlRuleSet",
    "ScopeDownStatement": {
      "NotStatement": {
        "Statement": {
          "ByteMatchStatement": {
            "FieldToMatch": { "Method": {} },
            "PositionalConstraint": "EXACTLY",
            "SearchString": "OPTIONS",
            "TextTransformations": [{ "Priority": 0, "Type": "NONE" }]
          }
        }
      }
    }
  }
}
```

This tells WAF: "Only evaluate Bot Control rules on requests that are NOT OPTIONS."

### Verification

```bash
challenge-validator test https://yoursite.com --profile aws-waf --suite cors
```

---

## 2. Token Refresh in Single-Page Apps

### Problem

The AWS WAF JS SDK (`awsWafIntegration` / `jsapi.js`) acquires a token on page load but does NOT auto-refresh it. In SPAs that don't do full page reloads, the token expires after `token_ttl_seconds` (default: 300s / 5 minutes).

### Root Cause

The SDK is designed for traditional multi-page apps where each navigation triggers a fresh page load and token acquisition. SPAs break this assumption.

### Fix — Option 1: Timer-based refresh

```javascript
// Refresh every 4 minutes (before the 5-minute TTL)
setInterval(() => {
  AwsWafIntegration.getToken();
}, 240_000);
```

### Fix — Option 2: Pre-request refresh

```javascript
async function fetchWithWafToken(url, options = {}) {
  await AwsWafIntegration.getToken();
  return fetch(url, { ...options, credentials: 'include' });
}
```

Option 2 is more reliable but adds latency to every request. Option 1 is better for most apps.

### Verification

```bash
challenge-validator test https://yoursite.com --profile aws-waf --token <token> --token-ttl 30
```

---

## 3. Rate-Limit + Bot Control Independence (Solve-Then-Block Loop)

### Problem

A user solves the CAPTCHA/challenge, then immediately gets rate-limited. The challenge and rate-limit rules are independent — both fire on the same traffic.

### Root Cause

1. Bot Control challenges the user (CAPTCHA or Silent Challenge)
2. The user's browser retries queued requests after solving
3. The rate-limit rule sees a burst of requests and blocks with 429
4. The user sees "blocked" right after solving the challenge

### Fix

Add a scope-down statement to your rate-limit rule that excludes requests carrying a valid `aws-waf-token`:

```json
{
  "Name": "RateLimitRule",
  "Statement": {
    "RateBasedStatement": {
      "Limit": 1000,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "NotStatement": {
          "Statement": {
            "ByteMatchStatement": {
              "FieldToMatch": { "SingleHeader": { "Name": "cookie" } },
              "PositionalConstraint": "CONTAINS",
              "SearchString": "aws-waf-token=",
              "TextTransformations": [{ "Priority": 0, "Type": "NONE" }]
            }
          }
        }
      }
    }
  },
  "Action": { "Block": {} }
}
```

This means: "Only rate-limit requests that DON'T have a WAF token" — recently-challenged users get a grace period.

### Verification

```bash
challenge-validator test https://yoursite.com --profile aws-waf --token <token> --suite post-challenge,score
```

---

## 4. CAPTCHA (405) vs. Silent Challenge (202)

### Problem

AWS WAF has two distinct challenge mechanisms that return different HTTP status codes, which can confuse monitoring and error handling.

### How They Work

| Mechanism | Status Code | User Experience | When Used |
|-----------|-------------|-----------------|-----------|
| CAPTCHA action | **405** | Interactive puzzle page | High-risk requests, explicit CAPTCHA rules |
| Challenge action (Silent) | **202** | Invisible JS challenge, brief loading screen | Medium-risk requests, Bot Control default |

Both mechanisms set the `aws-waf-token` cookie on success.

### What to Do

- **Don't hardcode 403 as the only "blocked" status.** Check for 405 and 202 as well.
- **In your error handling**, treat 405 as "show CAPTCHA" and 202 as "wait for JS challenge to complete."
- **In your monitoring**, alert on 405 (user friction) separately from 202 (invisible).

```javascript
// SPA error handler
if (response.status === 405) {
  showCaptchaModal();
} else if (response.status === 202) {
  // Silent challenge — SDK handles it, retry after short delay
  await new Promise(r => setTimeout(r, 2000));
  return fetch(url, options);
}
```

---

## 5. No Numeric Bot Score in Headers

### Problem

Unlike Cloudflare (which exposes `cf-bot-score`) or reCAPTCHA (which returns a 0-1 score), AWS WAF Bot Control does NOT expose a numeric score in HTTP response headers.

### How AWS WAF Classifies Bots

AWS WAF uses **labels** instead of scores. Labels are applied server-side during WAF rule evaluation and are visible in WAF logs, but NOT in HTTP responses.

Example labels:
- `awswaf:managed:aws:bot-control:bot:category:http_library`
- `awswaf:managed:aws:bot-control:signal:automated_browser`
- `awswaf:managed:aws:bot-control:bot:verified`

### How to Inspect Bot Signals

Enable WAF logging and query with CloudWatch Logs Insights:

```
fields @timestamp, httpRequest.clientIp, httpRequest.uri
| parse @message '"labels":[*]' as labels
| filter labels like /bot-control/
| sort @timestamp desc
| limit 100
```

### Impact on Testing

The `score_threshold` and `score_transparency` tests are **skipped** when using the `aws-waf` profile because there are no score headers to inspect.

---

## 6. Mobile SDK Access

### Problem

The AWS WAF mobile SDK (token provider for iOS/Android) is NOT available by default. It requires explicit opt-in through the AWS WAF console.

### How to Enable

1. Open the **AWS WAF console** → select your web ACL
2. Go to the **Application integration** tab
3. Click **Enable** under "Mobile SDK"
4. Note the **integration URL** provided
5. Add the SDK to your mobile app:
   - **iOS**: Available via CocoaPods (`AWSWAFMobileSDK`)
   - **Android**: Available via Maven (`com.amazonaws:aws-waf-mobile-sdk`)

### Mobile Integration Pattern

```swift
// iOS
import AWSWAFMobileSDK

let tokenProvider = WAFTokenProvider(url: URL(string: "https://your-integration-url")!)
let token = try await tokenProvider.getToken()

var request = URLRequest(url: apiURL)
request.setValue(token, forHTTPHeaderField: "x-aws-waf-token")
```

```kotlin
// Android
val tokenProvider = WAFTokenProvider.builder()
    .applicationIntegrationUrl("https://your-integration-url")
    .build()
val token = tokenProvider.getToken()

val request = Request.Builder()
    .url(apiUrl)
    .header("x-aws-waf-token", token)
    .build()
```

### Testing Limitation

This tool cannot test mobile SDK integration programmatically. Use the mobile SDK's built-in diagnostics or test with:

```bash
# Test the API endpoint your mobile app calls
challenge-validator test https://api.yoursite.com/mobile --profile aws-waf --token <waf-token>
```

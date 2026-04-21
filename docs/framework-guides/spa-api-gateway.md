# SPA + API Gateway + Challenge Tokens

## The Problem

Single-page apps behind API Gateway face two issues:
1. API calls get HTML challenge pages instead of JSON errors
2. CORS preflight (OPTIONS) requests get blocked by WAF rules

## Solution

### 1. Configure WAF to return JSON for API paths

In your AWS WAF custom response:
```json
{
  "CustomResponseBodies": {
    "ChallengeRequired": {
      "ContentType": "APPLICATION_JSON",
      "Content": "{\"error\":\"challenge_required\",\"message\":\"Please complete the challenge\"}"
    }
  }
}
```

### 2. Exempt OPTIONS from WAF rules

Add a high-priority rule:
```json
{
  "Name": "AllowPreflight",
  "Priority": 0,
  "Statement": {
    "ByteMatchStatement": {
      "FieldToMatch": { "Method": {} },
      "PositionalConstraint": "EXACTLY",
      "SearchString": "OPTIONS"
    }
  },
  "Action": { "Allow": {} }
}
```

### 3. Handle challenges in your SPA

```javascript
// API client interceptor
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 403 &&
        error.response?.data?.error === 'challenge_required') {
      await showChallengeModal();
      return api.request(error.config); // retry
    }
    throw error;
  }
);
```

### 4. Embed the challenge SDK

Load the WAF challenge SDK on your SPA's index page so tokens are acquired automatically:
```html
<script src="https://your-waf-domain/challenge.js" defer></script>
```

## Verification

```bash
challenge-validator test https://api.yoursite.com --token <token> --suite cors,token
```
